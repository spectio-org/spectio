/*
 * nf-spectio: appends Nextflow's TraceObserverV2 events to the spool of a driven run.
 *
 * Contract: api-and-data-model.md §14.1 (envelope, file names, bounds, allow-lists); behaviour:
 * architecture-plugins-and-packaging.md §13.1 (spool first), §13.3 (hooks only enqueue, never
 * throw), §13.4 (floor 25.04, in build.sh). Ported from the spike T2 prototype (branch
 * spike/engine-events), which posted each event over HTTP.
 *
 * The plugin is silent unless SPECTIO_RUN_ID, SPECTIO_LAUNCH_N and SPECTIO_SPOOL_DIR are set.
 * Hooks build a small map of allow-listed values and enqueue it; one writer thread appends the
 * lines and rotates. Every Throwable is caught; errors go to <spool dir>/../bridge.err.
 * Never sent: the task's script and env (P1 Assumption 3), the error report, and the error
 * message when it is the failing task's stderr (SEC-P3T1-09, FU-P3-08).
 */
package spectio

import groovy.json.JsonOutput
import java.nio.ByteBuffer
import java.nio.channels.FileChannel
import java.nio.charset.StandardCharsets
import java.nio.file.FileAlreadyExistsException
import java.nio.file.Files
import java.nio.file.LinkOption
import java.nio.file.Path
import java.nio.file.Paths
import java.nio.file.StandardOpenOption
import java.nio.file.attribute.PosixFilePermissions
import java.security.SecureRandom
import java.time.Instant
import java.util.concurrent.BlockingQueue
import java.util.concurrent.LinkedBlockingQueue
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicLong
import nextflow.BuildInfo
import nextflow.Session
import nextflow.plugin.BasePlugin
import nextflow.processor.TaskProcessor
import nextflow.trace.TraceObserverFactoryV2
import nextflow.trace.TraceObserverV2
import nextflow.trace.event.FilePublishEvent
import nextflow.trace.event.TaskEvent
import nextflow.trace.event.WorkflowOutputEvent
import org.pf4j.PluginWrapper

class SpectioPlugin extends BasePlugin {
    SpectioPlugin(PluginWrapper wrapper) { super(wrapper) }
}

class SpectioFactory implements TraceObserverFactoryV2 {
    @Override
    Collection<TraceObserverV2> create(Session session) {
        try {
            final spool = Spool.fromEnv(System.getenv())
            return spool ? [new SpectioObserver(spool)] as List<TraceObserverV2> : []
        } catch (Throwable e) {
            System.err.println("nf-spectio: disabled: $e")
            return []
        }
    }
}

/** The queue between the hooks and the one writer thread. */
class Spool {
    static final int QUEUE_CAPACITY = 100000
    private static final Object[] STOP = new Object[0]

    private final BlockingQueue<Object[]> queue = new LinkedBlockingQueue<>(QUEUE_CAPACITY)
    private final SpoolWriter writer
    private final Thread thread
    private final AtomicLong dropped = new AtomicLong()

    /** null when this is not a driven run (no variable set) or a variable is invalid. */
    static Spool fromEnv(Map<String, String> env) {
        final run = env.SPECTIO_RUN_ID, launch = env.SPECTIO_LAUNCH_N, dir = env.SPECTIO_SPOOL_DIR
        if (!run && !launch && !dir)
            return null
        if (!(run ==~ /run_[0-7][0-9A-HJKMNP-TV-Z]{25}/) || !(launch ==~ /[1-9][0-9]{0,18}/) || !dir) {
            System.err.println('nf-spectio: disabled: SPECTIO_RUN_ID, SPECTIO_LAUNCH_N or SPECTIO_SPOOL_DIR is invalid')
            return null
        }
        return new Spool(new SpoolWriter(Paths.get(dir), run, Long.parseLong(launch), SpoolWriter.ROTATE_BYTES))
    }

    Spool(SpoolWriter writer) {
        this.writer = writer
        thread = new Thread(this.&loop, 'nf-spectio-writer')
        thread.daemon = true
        thread.start()
        // Events can follow onFlowComplete (onFlowError), and Session's own shutdown callbacks
        // run before it (Session.groovy:919-936): the JVM's shutdown is the end of the stream.
        Runtime.runtime.addShutdownHook(new Thread(this.&close, 'nf-spectio-close'))
    }

    /** Called by the hooks: never blocks, never throws. A full queue drops and counts. */
    void enqueue(String type, Map data) {
        if (!queue.offer([type, System.currentTimeMillis(), data] as Object[]))
            dropped.incrementAndGet()
    }

    void error(String message) {
        enqueue(null, [message: message])
    }

    private void loop() {
        while (true) {
            try {
                final item = queue.take()
                if (item.is(STOP))
                    return
                if (item[0] == null)
                    writer.error((String) ((Map) item[2]).message)
                else
                    writer.write((String) item[0], (long) item[1], (Map) item[2])
            } catch (Throwable e) {
                writer.error("writer: $e")
            }
        }
    }

    void close() {
        try {
            queue.offer(STOP, 5, TimeUnit.SECONDS)
            thread.join(10000)
            // A writer stuck in I/O holds the writer's monitor: waiting on it would keep the
            // head from exiting, and closing under it would let it open a new file (SEC-P3T06-02).
            if (thread.alive) {
                System.err.println("nf-spectio: close: the writer thread is still running; ${dropped.get()} events dropped")
                return
            }
            writer.finish(dropped.get())
            writer.close()
        } catch (Throwable e) {
            System.err.println("nf-spectio: close: $e")
        }
    }
}

/** Appends envelopes to <dir>/nf-spectio-<launch>-<nnnn>.jsonl (api §14.1). One thread only. */
class SpoolWriter {
    static final String PRODUCER = 'nf-spectio/0.0.1'
    static final int MAX_LINE_BYTES = 65536
    static final long ROTATE_BYTES = 33554432
    static final int MAX_ERROR_LINES = 100
    private static final String CROCKFORD = '0123456789ABCDEFGHJKMNPQRSTVWXYZ'
    private static final def PRIVATE_DIR = PosixFilePermissions.asFileAttribute(PosixFilePermissions.fromString('rwx------'))
    private static final def PRIVATE_FILE = PosixFilePermissions.asFileAttribute(PosixFilePermissions.fromString('rw-------'))

    private final Path dir
    private final Path errFile
    private final String run
    private final long launch
    private final long rotateBytes
    private final SecureRandom random = new SecureRandom()
    private FileChannel out
    private Path path
    private long size
    private int index
    private long seq
    private int errors

    SpoolWriter(Path dir, String run, long launch, long rotateBytes) {
        this.dir = dir
        this.errFile = dir.parent.resolve('bridge.err')
        this.run = run
        this.launch = launch
        this.rotateBytes = rotateBytes
    }

    synchronized void write(String type, long ms, Map data) {
        try {
            final envelope = [v: 1, id: 'evt_' + ulid(ms), run: run, launch: launch, producer: PRODUCER,
                              seq: seq + 1, time: Instant.ofEpochMilli(ms).toString(), type: type, data: data]
            final bytes = (JsonOutput.toJson(envelope) + '\n').getBytes(StandardCharsets.UTF_8)
            if (bytes.length - 1 > MAX_LINE_BYTES) {
                error("$type: line over $MAX_LINE_BYTES bytes, dropped")
                return
            }
            if (out == null || size + bytes.length > rotateBytes)
                next()
            final buf = ByteBuffer.wrap(bytes)
            while (buf.hasRemaining())
                out.write(buf)
            size += bytes.length
            seq++
        } catch (Throwable e) {
            // A failed write (ENOSPC, EFBIG, a quota) does not rotate: a new file per event
            // would burn the indexes and the reader's file cap (CR-P3T06-01). Reopen only
            // when the file itself is gone. The partial line is cut off, so `size` stays exact and
            // no torn line is left behind by a later rotation (CR-P3T06-02).
            error("$type: not written: $e")
            if (out != null) {
                try {
                    out.truncate(size)
                } catch (Throwable ignored) {
                    close()
                }
                if (!Files.isRegularFile(path, LinkOption.NOFOLLOW_LINKS))
                    close()
            }
        }
    }

    /** Open the next file that does not exist yet, never one another writer made; reopen the
     *  current file instead while it is still empty. */
    private void next() {
        close()
        if (path != null && size == 0 && Files.isRegularFile(path, LinkOption.NOFOLLOW_LINKS)) {
            out = open(path)
            return
        }
        Files.createDirectories(dir, PRIVATE_DIR)
        while (true) {
            if (index >= 9999)
                throw new IOException('no spool file index left')
            final candidate = dir.resolve(String.format('nf-spectio-%d-%04d.jsonl', launch, index + 1))
            try {
                Files.createFile(candidate, PRIVATE_FILE)
            } catch (FileAlreadyExistsException ignored) {
                index++
                continue
            }
            index++
            path = candidate
            size = 0
            out = open(path)
            return
        }
    }

    private static FileChannel open(Path p) {
        FileChannel.open(p, StandardOpenOption.WRITE, StandardOpenOption.APPEND, LinkOption.NOFOLLOW_LINKS)
    }

    synchronized void close() {
        try {
            out?.close()
        } catch (Throwable ignored) {
        }
        out = null
    }

    /** One line in bridge.err, at most MAX_ERROR_LINES of them; never throws. */
    synchronized void error(String message) {
        if (errors++ < MAX_ERROR_LINES)
            log(message)
    }

    /** The close-time lines, past the cap (CR-P3T06-04). */
    synchronized void finish(long dropped) {
        if (errors > MAX_ERROR_LINES)
            log("${errors - MAX_ERROR_LINES} further errors not logged")
        if (dropped)
            log("$dropped events dropped: the queue was full")
    }

    private void log(String message) {
        try {
            try {
                Files.createFile(errFile, PRIVATE_FILE)
            } catch (FileAlreadyExistsException ignored) {
            }
            // A FIFO or device in its place would block the open forever (SEC-P3T06-02).
            if (!Files.isRegularFile(errFile, LinkOption.NOFOLLOW_LINKS))
                throw new IOException("$errFile is not a regular file")
            final line = "${Instant.now()} nf-spectio: $message\n".toString().getBytes(StandardCharsets.UTF_8)
            Files.write(errFile, line, StandardOpenOption.APPEND, LinkOption.NOFOLLOW_LINKS)
        } catch (Throwable e) {
            System.err.println("nf-spectio: $message ($e)")
        }
    }

    private String ulid(long ms) {
        final rnd = new byte[10]
        random.nextBytes(rnd)
        BigInteger n = BigInteger.valueOf(ms).shiftLeft(80).or(new BigInteger(1, rnd))
        final chars = new char[26]
        for (int i = 25; i >= 0; i--) {
            chars[i] = CROCKFORD.charAt(n.intValue() & 31)
            n = n.shiftRight(5)
        }
        return new String(chars)
    }
}

/** Builds each hook's allow-listed data (api §14.1) and enqueues it. */
class SpectioObserver implements TraceObserverV2 {
    static final int MAX_MESSAGE_CHARS = 4096
    static final int NO_EXIT = Integer.MAX_VALUE  // a task with no exit status yet (FU-P3-07)
    // The trace record's keys of api §14.1: not script, env or hostname.
    static final List<String> TRACE_KEYS = [
        'task_id', 'hash', 'native_id', 'process', 'tag', 'name', 'status', 'exit', 'module', 'container',
        'cpus', 'time', 'disk', 'memory', 'attempt', 'submit', 'start', 'complete', 'duration', 'realtime',
        'queue', '%cpu', '%mem', 'rss', 'vmem', 'peak_rss', 'peak_vmem', 'rchar', 'wchar', 'syscr', 'syscw',
        'read_bytes', 'write_bytes', 'vol_ctxt', 'inv_ctxt', 'workdir', 'scratch', 'error_action',
        'cpu_model', 'accelerator', 'accelerator_type']
    static final List<String> WHERE_KEYS = ['native_id', 'workdir']

    private final Spool spool
    private volatile Session session

    SpectioObserver(Spool spool) { this.spool = spool }

    private void emit(String hook, Closure<Map> data) {
        try {
            final common = [runName: str(session?.runName), sessionId: str(session?.uniqueId)]
            spool.enqueue("nextflow.$hook".toString(), common + data.call())
        } catch (Throwable e) {
            spool.error("$hook: $e")
        }
    }

    private static String str(Object v) { v == null ? null : v.toString() }

    private static Long num(Object v) { v instanceof Number ? ((Number) v).longValue() : null }

    private static Long exit(Object v) { v instanceof Number && ((Number) v).intValue() == NO_EXIT ? null : num(v) }

    private static Map task(TaskEvent ev, boolean withTrace) {
        final h = ev?.handler
        final t = h?.task
        final data = [taskId: str(t?.id), hash: str(t?.hash), name: str(t?.name), process: str(t?.processor?.name),
                      tag: str(t?.config?.tag), attempt: num(t?.config?.attempt), status: str(h?.status),
                      exitStatus: exit(t?.exitStatus), errorAction: str(t?.errorAction),
                      cached: t?.cached instanceof Boolean ? t.cached : null, workDir: str(t?.workDir)]
        // Every task event carries the work directory and the executor's job ID (P1 Task 28):
        // the trace record of the other hooks is cut to those two (TaskHandler.groovy:218,
        // GridTaskHandler.groovy:528, nextflow v26.10.4).
        data.trace = trace(ev?.trace?.store, withTrace ? TRACE_KEYS : WHERE_KEYS)
        return data
    }

    private static Map trace(Map store, List<String> keys) {
        if (store == null)
            return null
        final out = [:]
        for (String k : keys) {
            if (store.containsKey(k))
                out[k] = str(k == 'exit' ? exit(store[k]) : store[k])
        }
        return out
    }

    @Override void onFlowCreate(Session s) {
        session = s
        emit('onFlowCreate') { [nextflow: str(BuildInfo.version), resume: s.resumeMode as Boolean, workDir: str(s.workDir)] }
    }

    @Override void onFlowBegin() { emit('onFlowBegin') { [:] } }

    @Override void onFlowComplete() {
        emit('onFlowComplete') {
            final meta = session?.workflowMetadata
            // WorkflowMetadata.setErrorAttributes: with a failed task, errorMessage is that task's
            // stderr (or stdout) and is not sent; otherwise it is Nextflow's own error.
            final message = session?.fault?.task != null ? null : str(meta?.errorMessage)
            [success: meta?.success as Boolean, exitStatus: exit(meta?.exitStatus),
             errorMessage: message?.take(MAX_MESSAGE_CHARS)]
        }
    }

    @Override void onProcessCreate(TaskProcessor p) { emit('onProcessCreate') { [process: str(p?.name), processId: num(p?.id)] } }

    @Override void onProcessTerminate(TaskProcessor p) { emit('onProcessTerminate') { [process: str(p?.name), processId: num(p?.id)] } }

    @Override void onTaskPending(TaskEvent e) { emit('onTaskPending') { task(e, false) } }

    @Override void onTaskSubmit(TaskEvent e) { emit('onTaskSubmit') { task(e, false) } }

    @Override void onTaskStart(TaskEvent e) { emit('onTaskStart') { task(e, false) } }

    @Override void onTaskComplete(TaskEvent e) { emit('onTaskComplete') { task(e, true) } }

    @Override void onTaskCached(TaskEvent e) { emit('onTaskCached') { task(e, true) } }

    @Override void onFlowError(TaskEvent e) { emit('onFlowError') { task(e, true) } }

    @Override void onWorkflowOutput(WorkflowOutputEvent e) {}  // not in the allow-list

    @Override void onFilePublish(FilePublishEvent e) {
        emit('onFilePublish') { [source: str(e?.source), target: str(e?.target), labels: e?.labels?.collect { str(it) }] }
    }

    // True: the task wrapper writes .command.trace, so the trace record has realtime, %cpu and
    // peak_rss (Session.groovy:545, BashWrapperBuilder.groovy:633-636, v26.10.4; P1 Task 28).
    @Override boolean enableMetrics() { true }
}

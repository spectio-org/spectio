/*
 * nf-spectio: appends Nextflow's TraceObserverV2 events to the spool of a driven run.
 *
 * Contract: api-and-data-model.md §14.1 (envelope, file names, bounds, allow-lists); behaviour:
 * architecture-plugins-and-packaging.md §13.1 (spool first), §13.3 (hooks only enqueue, never
 * throw), §13.4 (floor 25.04, in build.sh). Ported from the spike T2 prototype (branch
 * spike/engine-events), which posted each event over HTTP.
 *
 * A driven run sets SPECTIO_RUN_ID, SPECTIO_LAUNCH_N and SPECTIO_SPOOL_DIR. With none of them, the
 * run was started from a terminal (architecture §13.8): the plugin makes a run ID, writes the
 * spool in <launch dir>/.spectio/events/<run ID>-nf-spectio-<nnnn>.jsonl, launch 1, and the
 * pointer ~/.spectio/observed/<run ID>.json, so the server finds the run.
 * Hooks build a small map of allow-listed values and enqueue it; one writer thread appends the
 * lines and rotates. Every Throwable is caught; errors go to <spool dir>/../bridge.err.
 * Every file is opened relative to a checked directory, never through a symlink (dev-env §15.3
 * req. 12): .spectio and events must be private directories of the user.
 * Never sent: the task's script and env (P1 Assumption 3), the error report, and the error
 * message when it is the failing task's stderr (SEC-P3T1-09, FU-P3-08).
 */
package spectio

import groovy.json.JsonOutput
import java.nio.ByteBuffer
import java.nio.channels.SeekableByteChannel
import java.nio.charset.StandardCharsets
import java.nio.file.FileAlreadyExistsException
import java.nio.file.Files
import java.nio.file.LinkOption
import java.nio.file.NoSuchFileException
import java.nio.file.OpenOption
import java.nio.file.Path
import java.nio.file.Paths
import java.nio.file.SecureDirectoryStream
import java.nio.file.StandardOpenOption
import java.nio.file.attribute.BasicFileAttributeView
import java.nio.file.attribute.FileAttribute
import java.nio.file.attribute.PosixFileAttributeView
import java.nio.file.attribute.PosixFilePermission
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

    /** A driven run's spool, or a terminal run's (no variable set); null when a variable is
     *  invalid, or a terminal run's spool directory is refused. */
    static Spool fromEnv(Map<String, String> env) {
        final run = env.SPECTIO_RUN_ID, launch = env.SPECTIO_LAUNCH_N, dir = env.SPECTIO_SPOOL_DIR
        if (!run && !launch && !dir)
            return terminal(Paths.get(System.getProperty('user.dir')).toAbsolutePath().normalize(),
                            Paths.get(env.HOME ?: System.getProperty('user.home')))
        if (!(run ==~ /run_[0-7][0-9A-HJKMNP-TV-Z]{25}/) || !(launch ==~ /[1-9][0-9]{0,18}/) || !dir) {
            System.err.println('nf-spectio: disabled: SPECTIO_RUN_ID, SPECTIO_LAUNCH_N or SPECTIO_SPOOL_DIR is invalid')
            return null
        }
        return new Spool(new SpoolWriter(Paths.get(dir), run, Long.parseLong(launch), SpoolWriter.ROTATE_BYTES))
    }

    /** A run started from a terminal in `launchDir`: a new run ID, launch 1, and the pointer. */
    static Spool terminal(Path launchDir, Path home) {
        final run = 'run_' + SpoolWriter.ulid(System.currentTimeMillis())
        final writer = new SpoolWriter(launchDir.resolve('.spectio').resolve('events'), run, 1L,
                                       SpoolWriter.ROTATE_BYTES, true)
        if (!writer.start())
            return null  // said once; no spool, so no pointer: nothing to show
        Pointer.write(writer, launchDir, home)
        return new Spool(writer)
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

/** `~/.spectio/observed/<run ID>.json` of a terminal run (architecture §13.8). */
class Pointer {
    /** Written 0600 under a temporary name, then renamed, only when ~/.spectio and observed/
     *  (made 0700) are private directories of the user (req. 12). No ~/.spectio: no pointer,
     *  silently. Any other error is said once in bridge.err and swallowed (architecture §13.3). */
    static void write(SpoolWriter writer, Path launchDir, Path home) {
        final run = writer.run
        SecureDirectoryStream<Path> top = null, spectio = null, observed = null
        try {
            top = SpoolWriter.openDir(home)
            try {
                spectio = SpoolWriter.privateDir(top, home, '.spectio', false)
            } catch (NoSuchFileException ignored) {
                return  // Spectio is not installed: the spool only
            }
            observed = SpoolWriter.privateDir(spectio, home.resolve('.spectio'), 'observed', true)
            final stat = new File('/proc/self/stat').text
            final data = [run_id: run, launch_dir: launchDir.toString(), engine: 'nextflow',
                          engine_version: BuildInfo.version?.toString(),
                          bridge_version: SpoolWriter.PRODUCER.split('/')[1],
                          host: new File('/proc/sys/kernel/hostname').text.trim(),
                          pid: ProcessHandle.current().pid(),
                          pid_start_time: stat.substring(stat.lastIndexOf(') ') + 2).trim().split(' ')[19],
                          boot_id: new File('/proc/sys/kernel/random/boot_id').text.trim()]
            final tmp = Paths.get(".${run}.json.tmp".toString())
            final options = [StandardOpenOption.WRITE, StandardOpenOption.CREATE_NEW, LinkOption.NOFOLLOW_LINKS] as Set<OpenOption>
            final ch = observed.newByteChannel(tmp, options, SpoolWriter.PRIVATE_FILE)
            try {
                final buf = ByteBuffer.wrap(JsonOutput.toJson(data).getBytes(StandardCharsets.UTF_8))
                while (buf.hasRemaining())
                    ch.write(buf)
            } finally {
                ch.close()
            }
            observed.move(tmp, observed, Paths.get("${run}.json".toString()))
        } catch (Throwable e) {
            writer.error("no pointer written in ~/.spectio/observed: $e")
        } finally {
            for (d in [observed, spectio, top]) {
                try { d?.close() } catch (Throwable ignored) {}
            }
        }
    }
}

/** Appends envelopes to <dir>/nf-spectio-<launch>-<nnnn>.jsonl, a terminal run's to
 *  <dir>/<run ID>-nf-spectio-<nnnn>.jsonl (api §14.1). One thread only. */
class SpoolWriter {
    static final String PRODUCER = 'nf-spectio/0.0.1'
    static final int MAX_LINE_BYTES = 65536
    static final long ROTATE_BYTES = 33554432
    static final int MAX_ERROR_LINES = 100
    private static final String CROCKFORD = '0123456789ABCDEFGHJKMNPQRSTVWXYZ'
    static final FileAttribute PRIVATE_DIR = PosixFilePermissions.asFileAttribute(PosixFilePermissions.fromString('rwx------'))
    static final FileAttribute PRIVATE_FILE = PosixFilePermissions.asFileAttribute(PosixFilePermissions.fromString('rw-------'))
    private static final Set<PosixFilePermission> NOT_PRIVATE = PosixFilePermissions.fromString('---rwxrwx')
    private static final SecureRandom RANDOM = new SecureRandom()
    private static final Path ERR = Paths.get('bridge.err')

    private final Path dir
    final String run
    private final long launch
    private final long rotateBytes
    private final boolean terminal
    private SecureDirectoryStream<Path> parentDir  // .spectio, which holds bridge.err
    private SecureDirectoryStream<Path> eventsDir
    private boolean broken  // the directory was refused: nothing more is tried
    private SeekableByteChannel out
    private Path path
    private long size
    private int index
    private long seq
    private int errors

    SpoolWriter(Path dir, String run, long launch, long rotateBytes, boolean terminal = false) {
        this.dir = dir
        this.run = run
        this.launch = launch
        this.rotateBytes = rotateBytes
        this.terminal = terminal
    }

    /** `dir` as given (the launch directory or the home, not checked). */
    static SecureDirectoryStream<Path> openDir(Path dir) {
        final ds = Files.newDirectoryStream(dir)
        if (ds instanceof SecureDirectoryStream)
            return (SecureDirectoryStream<Path>) ds
        ds.close()
        throw new IOException("$dir: no secure directory stream on this file system")
    }

    /** `name` in `parent` (at `parentPath`), made 0700 when `create`; refused unless a directory
     *  of this user that group and others cannot use, opened without following a symlink. */
    static SecureDirectoryStream<Path> privateDir(SecureDirectoryStream<Path> parent, Path parentPath, String name, boolean create) {
        if (create) {
            try {
                Files.createDirectory(parentPath.resolve(name), PRIVATE_DIR)
            } catch (FileAlreadyExistsException ignored) {
            }
        }
        final ds = parent.newDirectoryStream(Paths.get(name), LinkOption.NOFOLLOW_LINKS)
        final attrs = ds.getFileAttributeView(PosixFileAttributeView).readAttributes()
        final me = parentPath.fileSystem.userPrincipalLookupService.lookupPrincipalByName(System.getProperty('user.name'))
        if (attrs.owner() != me || !attrs.permissions().disjoint(NOT_PRIVATE)) {
            ds.close()
            throw new IOException("$name is not a private directory of yours (${attrs.owner()}, ${PosixFilePermissions.toString(attrs.permissions())})")
        }
        return ds
    }

    /** Open .spectio and events, once; false, with one line said, when refused. */
    synchronized boolean start() {
        if (eventsDir != null || broken)
            return !broken
        SecureDirectoryStream<Path> top = null
        try {
            final spectio = dir.parent
            Files.createDirectories(spectio.parent)  // the launch directory, as given
            top = openDir(spectio.parent)
            parentDir = privateDir(top, spectio.parent, spectio.fileName.toString(), true)
            eventsDir = privateDir(parentDir, spectio, dir.fileName.toString(), true)
        } catch (Throwable e) {  // read-only, refused, a symlink: no event of this launch
            broken = true
            error("the spool directory is refused, no events are written: $e")
        } finally {
            try { top?.close() } catch (Throwable ignored) {}
        }
        return !broken
    }

    synchronized void write(String type, long ms, Map data) {
        if (!start())
            return
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
                if (!isRegularFile(eventsDir, path))
                    close()
            }
        }
    }

    private static boolean isRegularFile(SecureDirectoryStream<Path> ds, Path name) {
        try {
            return ds.getFileAttributeView(name, BasicFileAttributeView, LinkOption.NOFOLLOW_LINKS).readAttributes().regularFile
        } catch (IOException ignored) {
            return false
        }
    }

    /** Open the next file that does not exist yet, never one another writer made; reopen the
     *  current file instead while it is still empty. */
    private void next() {
        close()
        if (path != null && size == 0 && isRegularFile(eventsDir, path)) {
            out = eventsDir.newByteChannel(path, [StandardOpenOption.WRITE, StandardOpenOption.APPEND, LinkOption.NOFOLLOW_LINKS] as Set<OpenOption>)
            return
        }
        final options = [StandardOpenOption.WRITE, StandardOpenOption.APPEND, StandardOpenOption.CREATE_NEW, LinkOption.NOFOLLOW_LINKS] as Set<OpenOption>
        while (true) {
            if (index >= 9999)
                throw new IOException('no spool file index left')
            final candidate = Paths.get(terminal ? String.format('%s-nf-spectio-%04d.jsonl', run, index + 1)
                                                 : String.format('nf-spectio-%d-%04d.jsonl', launch, index + 1))
            try {
                out = eventsDir.newByteChannel(candidate, options, PRIVATE_FILE)
            } catch (FileAlreadyExistsException ignored) {
                index++
                continue
            }
            index++
            path = candidate
            size = 0
            return
        }
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
        start()
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

    /** In .spectio/bridge.err, opened relative to the checked .spectio; on stderr without it. */
    private void log(String message) {
        try {
            if (parentDir == null)
                throw new IOException('.spectio is not open')
            try {
                parentDir.newByteChannel(ERR, [StandardOpenOption.WRITE, StandardOpenOption.CREATE_NEW, LinkOption.NOFOLLOW_LINKS] as Set<OpenOption>, PRIVATE_FILE).close()
            } catch (FileAlreadyExistsException ignored) {
            }
            // A FIFO or device in its place would block the open forever (SEC-P3T06-02).
            if (!isRegularFile(parentDir, ERR))
                throw new IOException("${dir.parent.resolve(ERR)} is not a regular file")
            final ch = parentDir.newByteChannel(ERR, [StandardOpenOption.WRITE, StandardOpenOption.APPEND, LinkOption.NOFOLLOW_LINKS] as Set<OpenOption>)
            try {
                final buf = ByteBuffer.wrap("${Instant.now()} nf-spectio: $message\n".toString().getBytes(StandardCharsets.UTF_8))
                while (buf.hasRemaining())
                    ch.write(buf)
            } finally {
                ch.close()
            }
        } catch (Throwable e) {
            System.err.println("nf-spectio: $message ($e)")
        }
    }

    static String ulid(long ms) {
        final rnd = new byte[10]
        RANDOM.nextBytes(rnd)
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
    // Every task hook (P1 Task 28), and the request the trace record carries from submission
    // on (TaskHandler.groovy:203-231, v26.10.4; P1 Task 33); the measured keys are final only.
    static final List<String> WHERE_KEYS = ['native_id', 'workdir']
    static final List<String> REQUEST_KEYS = ['cpus', 'memory', 'time', 'disk', 'queue', 'accelerator',
                                              'accelerator_type', 'attempt']
    static final int MAX_CONFIG_DEPTH = 8

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
        data.trace = trace(ev?.trace?.store, withTrace ? TRACE_KEYS : WHERE_KEYS + REQUEST_KEYS)
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

    /** True when the process config, or one of its selectors (`withName:`, `withLabel:`), sets
     *  `clusterOptions`. Raw sbatch text: only that it is set is sent (SEC-P3T1-11). A directive
     *  written in the script itself is not in the config, so not seen here. */
    static boolean setsClusterOptions(Object config, int depth = 0) {
        if (!(config instanceof Map) || depth > MAX_CONFIG_DEPTH)
            return false
        return ((Map) config).any { k, v -> k == 'clusterOptions' ? v != null : setsClusterOptions(v, depth + 1) }
    }
    @Override void onFlowCreate(Session s) {
        session = s
        emit('onFlowCreate') {
            // As Session.cleanup() reads it: `!config.cleanup` by Groovy truth (Session.groovy:1375-1410;
            // its bytecode read in the 26.10.4 jar, 2026-11-07).
            [nextflow: str(BuildInfo.version), resume: s.resumeMode as Boolean, workDir: str(s.workDir),
             cleanup: s.config?.cleanup ? true : false, clusterOptionsSet: setsClusterOptions(s.config?.process),
             target: moduleTarget(str(s.commandLine), s.workflowMetadata?.scriptFile, str(s.workflowMetadata?.scriptId))]
        }
    }

    static final int MAX_TARGET_FILE = 65536
    static final List<String> GLOBAL_WITH_VALUE = ['-c', '-C', '-config', '-log', '-syslog', '-trace']
    static final java.util.regex.Pattern REGISTRY_NAME = ~/[a-z0-9][a-z0-9_-]{0,63}\/[a-z0-9][a-z0-9_.-]{0,127}/
    static final java.util.regex.Pattern HEX = ~/[0-9a-f]{64}/

    /** `nextflow module run` (Nextflow >= 26.04): the module this run targets, or null for a
     *  pipeline run (api §5.9, architecture §13.8). The command line is parsed here and never sent;
     *  a registry module's checksum is its `.module-info`'s, a local one's hash is the script ID. */
    static Map moduleTarget(String commandLine, Object scriptFile, String scriptId) {
        final words = (commandLine ?: '').take(MAX_MESSAGE_CHARS).trim().split(/\s+/) as List<String>
        int at = 1  // the first word is the launcher; then its own options, then the command
        while (at < words.size() && words[at].startsWith('-'))
            at += words[at] in GLOBAL_WITH_VALUE ? 2 : 1
        if (at + 2 >= words.size() || words[at] != 'module' || words[at + 1] != 'run' || words[at + 2].startsWith('-'))
            return null
        final ref = words[at + 2]
        final v = words.indexOf('-version')
        final version = v > at && v + 1 < words.size() ? words[v + 1].take(64) : null
        final Path dir = scriptFile instanceof Path ? ((Path) scriptFile).parent : null
        if (REGISTRY_NAME.matcher(ref).matches() && !ref.startsWith('/') && !ref.startsWith('.')) {
            final info = dir == null ? null : smallText(dir.resolve('.module-info'))
            final checksum = info?.readLines()?.find { it.startsWith('checksum=') }?.substring(9)?.trim()
            return [kind: 'module', name: ref, version: version, source: 'registry',
                    hash: checksum && HEX.matcher(checksum).matches() ? checksum : null]
        }
        final meta = dir == null ? null : smallText(dir.resolve('meta.yml'))
        final name = yamlScalar(meta, 'name') ?: dir?.fileName?.toString() ?: ref
        return [kind: 'module', name: name.take(MAX_MESSAGE_CHARS), version: yamlScalar(meta, 'version')?.take(64),
                source: 'local', path: dir?.toString(), hash: scriptId]
    }

    /** A small regular file's text, never through a symlink; null otherwise. */
    static String smallText(Path file) {
        try {
            if (!Files.isRegularFile(file, LinkOption.NOFOLLOW_LINKS) || Files.size(file) > MAX_TARGET_FILE)
                return null
            return new String(Files.readAllBytes(file), StandardCharsets.UTF_8)
        } catch (Exception ignored) {
            return null
        }
    }

    /** A top-level `key: value` of a YAML file, quotes removed: enough for `meta.yml`'s name and version. */
    static String yamlScalar(String text, String key) {
        if (text == null)
            return null
        final m = text =~ /(?m)^${key}:[ \t]*["']?([^"'\r\n#]*?)["']?[ \t]*(#.*)?$/
        return m.find() && m.group(1) ? m.group(1) : null
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

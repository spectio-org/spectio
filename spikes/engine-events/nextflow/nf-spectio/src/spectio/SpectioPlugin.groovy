/*
 * Spike T2: a first nf-spectio. Posts every TraceObserverV2 event as JSON to $SPECTIO_ENDPOINT.
 * Interface read with `javap` from the nextflow-26.10.4 and 25.10.9 -dist jars (identical method
 * lists): nextflow.trace.TraceObserverV2, TraceObserverFactoryV2 (an org.pf4j.ExtensionPoint),
 * nextflow.trace.event.{TaskEvent, FilePublishEvent, WorkflowOutputEvent}.
 * Built without Gradle: compiled with the Groovy compiler inside the Nextflow jar (build.sh).
 */
package spectio

import groovy.json.JsonOutput
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
        final url = System.getenv('SPECTIO_ENDPOINT')
        return url ? [new SpectioObserver(url)] as List<TraceObserverV2> : []
    }
}

class SpectioObserver implements TraceObserverV2 {
    private final String url
    private Session session
    private int seq = 0

    SpectioObserver(String url) { this.url = url }

    private synchronized void post(String hook, Map data) {
        final body = [seq: ++seq, hook: hook, instant: System.currentTimeMillis(),
                      runName: session?.runName, sessionId: session?.uniqueId?.toString()] + data
        try {
            final conn = (HttpURLConnection) new URL(url).openConnection()
            conn.requestMethod = 'POST'
            conn.doOutput = true
            conn.setRequestProperty('Content-Type', 'application/json')
            conn.outputStream.withWriter('UTF-8') { it << JsonOutput.toJson(body) }
            conn.responseCode
            conn.disconnect()
        } catch (Exception e) {
            System.err.println("nf-spectio: post failed: $e")
        }
    }

    private static Map task(TaskEvent ev) {
        final h = ev.handler
        final t = h?.task
        return [taskId: t?.id?.toString(), name: t?.name, process: t?.processor?.name, tag: t?.config?.tag?.toString(),
                hash: t?.hash?.toString(), attempt: t?.config?.attempt, status: h?.status?.toString(),
                exitStatus: t?.exitStatus == Integer.MAX_VALUE ? null : t?.exitStatus, workDir: t?.workDir?.toString(),
                errorAction: t?.errorAction?.toString(), cached: t?.cached,
                trace: ev.trace?.store?.collectEntries { k, v -> [k, v?.toString()] }]
    }

    private static Map outputs(TaskEvent ev) {
        // checking-scenarios.md §11.1: outputs are collected before onTaskComplete (internal API)
        final out = ev.handler?.task?.outputs
        return out?.collectEntries { k, v -> [k.toString(), [type: k.getClass().simpleName, name: k.hasProperty('name') ? k.name : null,
                                                              value: v instanceof Collection ? v.collect { it.toString() } : v?.toString()]] } ?: [:]
    }

    @Override void onFlowCreate(Session s) {
        session = s
        post('onFlowCreate', [resume: s.resumeMode, workDir: s.workDir?.toString(), nextflow: nextflow.BuildInfo.version])
    }
    @Override void onFlowBegin() { post('onFlowBegin', [:]) }
    @Override void onFlowComplete() {
        post('onFlowComplete', [success: session?.workflowMetadata?.success, exitStatus: session?.workflowMetadata?.exitStatus,
                                errorMessage: session?.workflowMetadata?.errorMessage])
    }
    @Override void onProcessCreate(TaskProcessor p) { post('onProcessCreate', [process: p.name, processId: p.id]) }
    @Override void onProcessTerminate(TaskProcessor p) { post('onProcessTerminate', [process: p.name, processId: p.id]) }
    @Override void onTaskPending(TaskEvent e) { post('onTaskPending', task(e)) }
    @Override void onTaskSubmit(TaskEvent e) { post('onTaskSubmit', task(e)) }
    @Override void onTaskStart(TaskEvent e) { post('onTaskStart', task(e)) }
    @Override void onTaskComplete(TaskEvent e) { post('onTaskComplete', task(e) + [outputs: outputs(e)]) }
    @Override void onTaskCached(TaskEvent e) { post('onTaskCached', task(e) + [outputs: outputs(e)]) }
    @Override void onFlowError(TaskEvent e) { post('onFlowError', e ? task(e) : [:]) }
    @Override void onWorkflowOutput(WorkflowOutputEvent e) {
        post('onWorkflowOutput', [name: e.name, value: e.value?.toString(), index: e.index?.toString()])
    }
    @Override void onFilePublish(FilePublishEvent e) {
        post('onFilePublish', [source: e.source?.toString(), target: e.target?.toString(), labels: e.labels])
    }
    @Override boolean enableMetrics() { false }
}

// Spike D2: smallest local Nextflow pipeline (two processes, a channel, publishDir).
params.names = ['Bonjour', 'Hello', 'Hola']

process SAY {
    input:  val greeting
    output: path 'out.txt'
    script: "echo '${greeting} world' > out.txt"
}

process COLLECT {
    publishDir 'results', mode: 'copy'
    input:  path 'in*.txt'
    output: path 'all.txt'
    script: "cat in*.txt | sort > all.txt"
}

workflow {
    COLLECT(SAY(channel.fromList(params.names)).collect())
}

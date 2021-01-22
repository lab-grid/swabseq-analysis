$task=$args[0]
Invoke-WebRequest -UseBasicParsing http://localhost:5000/swabseq/076/$task

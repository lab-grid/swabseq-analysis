$task=$args[0]
Invoke-WebRequest -UseBasicParsing http://localhost:5000/script/$task

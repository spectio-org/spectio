#This is the script which updates the language server
#It basically purges everything and then makes everything again from scratch

import os

os.system("rm language-server-all.jar")

#TODO -> update this link once the changes have been integrated onto the main branch
os.system("git clone https://github.com/George-Marchment/language-server.git ./temp_folder")
os.system("rm -rf temp_folder/.git")
os.system("mkdir language-server")
os.system("mv temp_folder/* language-server")
os.system("rm -rf temp_folder/")

os.system("git clone https://github.com/nextflow-io/nextflow ./temp_folder")
os.system("rm -rf temp_folder/.git")
os.system("mkdir nextflow")
os.system("mv temp_folder/* nextflow")
os.system("rm -rf temp_folder/")


rest_of_script = '''cd language-server/
make
'''
os.system(rest_of_script)

os.system("cd ..")

os.system('mv language-server/build/libs/language-server-all.jar .')

os.system("rm -rf language-server/") 
os.system("rm -rf nextflow/")



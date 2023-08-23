# Fruit Loops Part 1 
import subprocess

def main():
    NUM_IT = 5
    for i in range(NUM_IT):
        variable_to_pass = [str(i)]
        subprocess.run(["python", "Fruit_Loops.py"] + variable_to_pass)

if __name__ == "__main__":
    main()
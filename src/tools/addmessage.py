import sys

PATH = "/home/sparrow/EVE/logs/Chatlogs/TheCitadel_20401229_065150.txt"


def main():
    with open(PATH, "r", encoding="utf-16") as f:
        content = f.read()
        lines = content.split("\n")
        line = lines[-2].strip()
        line = line[:line.find(">")+1]

    line = line + " " + sys.argv[1] + "\n"
    with open(PATH, "a", encoding='utf-16') as f:
        f.write(line)


if __name__ == "__main__":
    main()

    

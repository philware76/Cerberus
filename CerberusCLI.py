import sys

from Cerberus.cmdShells.mainShell import runShell
from show_image import displayImage

if __name__ == "__main__":
    displayImage(["Image1.png"])
    print("SmithMeyers - 2025")
    runShell(sys.argv)

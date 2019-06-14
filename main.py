import os
import sys
from AppSettings import *
from BusinessLogic import EntryPoint

def main():
    parser = EntryPoint.MainParser(search_settings)
    parser.start_console()

if __name__ == "__main__":
    main()
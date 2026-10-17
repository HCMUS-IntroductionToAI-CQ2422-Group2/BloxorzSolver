"""Run with python main.py from the project root."""
import multiprocessing


if __name__ == "__main__":
    multiprocessing.freeze_support()
    from FrontEnd.app import main
    main()

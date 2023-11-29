import time
from concurrent.futures import ThreadPoolExecutor
import threading


def long_running_task(task_number):
    print(f"Task {task_number} started")
    time.sleep(2)  # Simulate a task taking 2 seconds
    print(f"Task {task_number} finished")


def main():
    # Creating a ThreadPoolExecutor without specifying max_workers

    for i in range(100):
        thread = threading.Thread(
            target=long_running_task, args=(i,))
        thread.start()


if __name__ == "__main__":
    main()

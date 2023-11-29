import time
from concurrent.futures import ThreadPoolExecutor


def long_running_task(task_number):
    print(f"Task {task_number} started")
    time.sleep(2)  # Simulate a task taking 2 seconds
    print(f"Task {task_number} finished")


def main():
    # Creating a ThreadPoolExecutor without specifying max_workers
    with ThreadPoolExecutor() as executor:
        for i in range(100):
            executor.submit(long_running_task, i)


if __name__ == "__main__":
    main()

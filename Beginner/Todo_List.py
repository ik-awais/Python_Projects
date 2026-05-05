# To-Do List using Basic Concepts
# Simple To-Do List Manager
def display_menu():
    # Display the main menu options
    print("\n" + "="*40)
    print("\t  TO-DO LIST MANAGER")
    print("="*40)
    print("1. View all tasks")
    print("2. Add a new task")
    print("3. Mark task as completed")
    print("4. Delete a task")
    print("5. Exit")
    print("="*40)
def view_tasks(tasks):
    # Display all tasks with their status
    if not tasks:
        print("\nYour to-do list is empty!")
        return    
    print("\n" + "-"*40)
    print("YOUR TASKS:")
    print("-"*40)    
    for i, task in enumerate(tasks, 1):
        status = "✅" if task["completed"] else " "
        print(f"{i}. [{status}] {task['description']}")    
    # Count completed vs pending tasks
    completed_count = sum(1 for task in tasks if task["completed"])
    pending_count = len(tasks) - completed_count
    
    print("-"*40)
    print(f"Total: {len(tasks)} tasks ({pending_count} pending, {completed_count} completed)")
    print("-"*40)

def add_task(tasks):
    # Add a new task to the list
    print("\n" + "-"*40)
    print("ADD NEW TASK")
    print("-"*40)
    
    description = input("Enter the task description: ").strip()
    
    if description:
        # Create a dictionary to store task info
        new_task = {
            "description": description,
            "completed": False
        }
        tasks.append(new_task)
        print(f"\nTask added: '{description}'")
    else:
        print("\nTask not added - description cannot be empty!")

def mark_task_completed(tasks):
    # Mark a task as completed
    if not tasks:
        print("\nYour to-do list is empty!")
        return
    
    view_tasks(tasks)
    
    try:
        task_num = int(input("\nEnter the task number to mark as completed: "))
        
        if 1 <= task_num <= len(tasks):
            tasks[task_num - 1]["completed"] = True
            print(f"\nTask {task_num} marked as completed!")
        else:
            print(f"\nInvalid task number! Please enter a number between 1 and {len(tasks)}")
    except ValueError:
        print("\nPlease enter a valid number!")

def delete_task(tasks):
    # Delete a task from the list
    if not tasks:
        print("\nYour to-do list is empty!")
        return
    
    view_tasks(tasks)
    
    try:
        task_num = int(input("\nEnter the task number to delete: "))
        
        if 1 <= task_num <= len(tasks):
            deleted_task = tasks.pop(task_num - 1)
            print(f"\nDeleted task: '{deleted_task['description']}'")
        else:
            print(f"\nInvalid task number! Please enter a number between 1 and {len(tasks)}")
    except ValueError:
        print("\nPlease enter a valid number!")

def save_tasks_to_file(tasks, filename="todo_list.txt"):
    # Save tasks to a file
    try:
        with open(filename, "w") as file:
            for task in tasks:
                # Write each task on a new line: description,completed_status
                status = "1" if task["completed"] else "0"
                file.write(f"{task['description']},{status}\n")
        print(f"\nTasks saved to '{filename}'")
    except:
        print("\nError saving tasks to file")

def load_tasks_from_file(filename="todo_list.txt"):
    # Load tasks from a file
    tasks = []
    
    try:
        with open(filename, "r") as file:
            for line in file:
                line = line.strip()
                if line:
                    parts = line.split(",", 1)  # Split only on first comma
                    if len(parts) == 2:
                        description, status = parts
                        # Convert "1" to True, "0" to False
                        completed = (status == "1")
                        tasks.append({
                            "description": description,
                            "completed": completed
                        })
        print(f"Tasks loaded from '{filename}'")
    except FileNotFoundError:
        print(f"'{filename}' not found. Starting with an empty to-do list.")
    except:
        print("Error loading tasks from file. Starting with an empty to-do list.")
    
    return tasks

def main():
    # Main function to run the to-do list manager
    print("Welcome to the Simple To-Do List Manager!")
    
    # Load tasks from file if it exists
    tasks = load_tasks_from_file()
    
    while True:
        display_menu()
        
        choice = int(input("\nEnter your choice (1-5): ").strip())
        
        match choice:
            case 1:
                view_tasks(tasks)
            case 2: 
                add_task(tasks)
            case 3:
                mark_task_completed(tasks)
            case 4: 
                delete_task(tasks)
            case 5:
                # Save tasks before exiting
                save_tasks_to_file(tasks)
                print("\nThank you for using the To-Do List Manager. Goodbye!")
                break
            case _:
                print("\nInvalid choice! Please enter a number between 1 and 5.")
            
        input("\nPress Enter to continue...")

# Run the program
if __name__ == "__main__":
    main()
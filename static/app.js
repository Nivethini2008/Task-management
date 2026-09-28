let tasks = [];

document.addEventListener("DOMContentLoaded", () => {
    const taskForm = document.getElementById("task-form");

    if (taskForm) {
        loadTasks();
        taskForm.addEventListener("submit", saveTask);

        // WebSocket / real-time updates
        const socket = io();

        socket.on("connect", () => {
            socket.emit("join");
        });

        socket.on("task_created", task => {
            if (!tasks.some(t => t.id === task.id)) {
                tasks.unshift(task);
                renderTasks();
                showToast("New task created");
            }
        });

        socket.on("task_updated", task => {
            const index = tasks.findIndex(t => t.id === task.id);
            if (index !== -1) {
                tasks[index] = task;
                renderTasks();
                showToast("Task updated");
            }
        });

        socket.on("task_deleted", data => {
            tasks = tasks.filter(t => t.id !== data.id);
            renderTasks();
            showToast("Task deleted");
        });
    }
});


async function loadTasks() {
    try {
        const response = await fetch("/api/tasks");
        tasks = await response.json();
        renderTasks();
    } catch (error) {
        showToast("Could not load tasks");
    }
}


function renderTasks() {
    const list = document.getElementById("task-list");
    if (!list) return;

    const search = document.getElementById("search-input").value.toLowerCase();
    const status = document.getElementById("filter-status").value;
    const priority = document.getElementById("filter-priority").value;

    const filtered = tasks.filter(task => {
        const matchesSearch =
            task.title.toLowerCase().includes(search) ||
            task.description.toLowerCase().includes(search);

        const matchesStatus = status === "All" || task.status === status;
        const matchesPriority = priority === "All" || task.priority === priority;

        return matchesSearch && matchesStatus && matchesPriority;
    });

    updateStats();

    if (!filtered.length) {
        list.innerHTML = `
            <div class="empty">
                <h3>No tasks found</h3>
                <p>Create a task or change your filters.</p>
            </div>`;
        return;
    }

    list.innerHTML = filtered.map(task => `
        <article class="task-card">
            <h3>${escapeHtml(task.title)}</h3>
            <p>${escapeHtml(task.description || "No description")}</p>

            <div class="task-meta">
                <span class="badge ${statusClass(task.status)}">${escapeHtml(task.status)}</span>
                <span class="badge ${priorityClass(task.priority)}">${escapeHtml(task.priority)}</span>
                ${task.due_date ? `<span class="badge">${escapeHtml(task.due_date)}</span>` : ""}
            </div>

            <div class="task-actions">
                <button class="small-btn" onclick="openEditModal(${task.id})">Edit</button>
                <button class="small-btn delete" onclick="deleteTask(${task.id})">Delete</button>
            </div>
        </article>
    `).join("");
}


function updateStats() {
    document.getElementById("total-count").textContent = tasks.length;
    document.getElementById("pending-count").textContent =
        tasks.filter(t => t.status === "Pending").length;
    document.getElementById("progress-count").textContent =
        tasks.filter(t => t.status === "In Progress").length;
    document.getElementById("completed-count").textContent =
        tasks.filter(t => t.status === "Completed").length;
}


function openCreateModal() {
    document.getElementById("modal-title").textContent = "Add Task";
    document.getElementById("task-id").value = "";
    document.getElementById("task-title").value = "";
    document.getElementById("task-description").value = "";
    document.getElementById("task-status").value = "Pending";
    document.getElementById("task-priority").value = "Medium";
    document.getElementById("task-due-date").value = "";
    document.getElementById("task-modal").classList.remove("hidden");
}


function openEditModal(id) {
    const task = tasks.find(t => t.id === id);
    if (!task) return;

    document.getElementById("modal-title").textContent = "Edit Task";
    document.getElementById("task-id").value = task.id;
    document.getElementById("task-title").value = task.title;
    document.getElementById("task-description").value = task.description;
    document.getElementById("task-status").value = task.status;
    document.getElementById("task-priority").value = task.priority;
    document.getElementById("task-due-date").value = task.due_date || "";
    document.getElementById("task-modal").classList.remove("hidden");
}


function closeModal() {
    document.getElementById("task-modal").classList.add("hidden");
}


async function saveTask(event) {
    event.preventDefault();

    const id = document.getElementById("task-id").value;

    const data = {
        title: document.getElementById("task-title").value,
        description: document.getElementById("task-description").value,
        status: document.getElementById("task-status").value,
        priority: document.getElementById("task-priority").value,
        due_date: document.getElementById("task-due-date").value
    };

    try {
        const response = await fetch(
            id ? `/api/tasks/${id}` : "/api/tasks",
            {
                method: id ? "PUT" : "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(data)
            }
        );

        const result = await response.json();

        if (!response.ok) {
            showToast(result.error || "Something went wrong");
            return;
        }

        if (id) {
            const index = tasks.findIndex(t => t.id === Number(id));
            if (index !== -1) tasks[index] = result;
        } else {
            if (!tasks.some(t => t.id === result.id)) {
                tasks.unshift(result);
            }
        }

        closeModal();
        renderTasks();
        showToast(id ? "Task updated successfully" : "Task created successfully");
    } catch (error) {
        showToast("Server error");
    }
}


async function deleteTask(id) {
    if (!confirm("Are you sure you want to delete this task?")) return;

    try {
        const response = await fetch(`/api/tasks/${id}`, {
            method: "DELETE"
        });

        const result = await response.json();

        if (!response.ok) {
            showToast(result.error || "Could not delete task");
            return;
        }

        tasks = tasks.filter(task => task.id !== id);
        renderTasks();
        showToast("Task deleted successfully");
    } catch (error) {
        showToast("Server error");
    }
}


function statusClass(status) {
    if (status === "Completed") return "status-completed";
    if (status === "In Progress") return "status-progress";
    return "status-pending";
}


function priorityClass(priority) {
    if (priority === "High") return "priority-high";
    if (priority === "Low") return "priority-low";
    return "priority-medium";
}


function showToast(message) {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = "toast";
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => toast.remove(), 2500);
}


function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

export function initUpload() {
    const fileInput = document.getElementById('pdf-files');
    const fileListDiv = document.getElementById('file-list');
    const fileNamesUl = document.getElementById('file-names');
    const uploadForm = document.getElementById('upload-form');
    const uploadBtn = document.getElementById('upload-btn');
    const uploadStatus = document.getElementById('upload-status');

    if (!fileInput) return; // Guard clause for other pages

    fileInput.addEventListener('change', () => {
        fileNamesUl.innerHTML = '';
        if (fileInput.files.length > 0) {
            fileListDiv.classList.remove('hidden');
            Array.from(fileInput.files).forEach(file => {
                const li = document.createElement('li');
                li.textContent = `${file.name} (${(file.size/1024/1024).toFixed(2)} MB)`;
                fileNamesUl.appendChild(li);
            });
        } else {
            fileListDiv.classList.add('hidden');
        }
    });

    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (fileInput.files.length === 0) return;

        const formData = new FormData();
        Array.from(fileInput.files).forEach(file => formData.append('files', file));

        uploadBtn.disabled = true;
        uploadBtn.textContent = 'Processing...';
        uploadStatus.classList.add('hidden');

        try {
            const response = await fetch('http://localhost:8000/upload-pdf', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            
            if (response.ok) {
                uploadStatus.textContent = data.message || "Upload successful!";
                uploadStatus.className = 'p-4 rounded-lg text-sm bg-green-50 text-green-700 border border-green-200 block mt-4';
                fileInput.value = '';
                fileListDiv.classList.add('hidden');
            } else {
                throw new Error(data.detail || "Server error.");
            }
        } catch (err) {
            uploadStatus.textContent = err.message;
            uploadStatus.className = 'p-4 rounded-lg text-sm bg-red-50 text-red-700 border border-red-200 block mt-4';
        } finally {
            uploadBtn.disabled = false;
            uploadBtn.textContent = 'Process Documents';
        }
    });
}

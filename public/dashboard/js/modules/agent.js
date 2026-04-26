export function initAgent() {
    const chatMessages = document.getElementById('chat-messages');
    const textInput = document.getElementById('text-input');
    const sendBtn = document.getElementById('send-btn');
    const voiceBtn = document.getElementById('voice-btn');
    const recordingStatus = document.getElementById('recording-status');
    const loadingIndicator = document.getElementById('loading-indicator');
    const suggestionBtns = document.querySelectorAll('.suggestion-btn');

    if(!chatMessages) return;

    const API_URL = 'http://localhost:8000/ask-agent';
    let mediaRecorder;
    let audioChunks = [];
    let isRecording = false;

    async function sendTextMessage(text) {
        if (!text.trim()) return;
        
        appendUserMessage(text);
        textInput.value = '';
        showLoading();

        try {
            const response = await fetch(API_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: text })
            });
            
            if (!response.ok) throw new Error('Network response was not ok');
            
            const data = await response.json();
            hideLoading();
            appendAIMessage(data.answer);
            playTTS(data.answer);

        } catch (error) {
            console.error('Error:', error);
            hideLoading();
            appendAIMessage("Sorry, there was an error processing your request. Please ensure the FastAPI backend is running.");
        }
    }

    async function sendAudioMessage(audioBlob) {
        const tempMsgId = appendUserMessage("<i class='fa-solid fa-microphone mr-2'></i> Audio message...", true);
        showLoading();

        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.webm');

        try {
            const response = await fetch(API_URL, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) throw new Error('Network response was not ok');

            const data = await response.json();
            hideLoading();
            
            updateUserMessage(tempMsgId, `<i class='fa-solid fa-microphone mr-2'></i> ${data.transcribed_text}`);
            appendAIMessage(data.answer);
            playTTS(data.answer);

        } catch (error) {
            console.error('Error:', error);
            hideLoading();
            updateUserMessage(tempMsgId, "<i class='fa-solid fa-microphone-slash mr-2 text-red-300'></i> Audio message (Failed to transcribe)");
            appendAIMessage("Sorry, there was an error processing your audio.");
        }
    }

    sendBtn.addEventListener('click', () => sendTextMessage(textInput.value));
    textInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendTextMessage(textInput.value);
    });

    suggestionBtns.forEach(btn => {
        btn.addEventListener('click', () => sendTextMessage(btn.innerText));
    });

    voiceBtn.addEventListener('click', async () => {
        if (!isRecording) {
            startRecording();
        } else {
            stopRecording();
        }
    });

    async function startRecording() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];

            mediaRecorder.ondataavailable = event => {
                if (event.data.size > 0) audioChunks.push(event.data);
            };

            mediaRecorder.onstop = () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                sendAudioMessage(audioBlob);
                stream.getTracks().forEach(track => track.stop());
            };

            mediaRecorder.start();
            isRecording = true;
            
            voiceBtn.classList.remove('bg-gray-100', 'dark:bg-gray-700', 'text-gray-600', 'dark:text-gray-300');
            voiceBtn.classList.add('bg-red-500', 'text-white', 'pulse-recording');
            recordingStatus.classList.remove('hidden');
            textInput.disabled = true;
            textInput.placeholder = "Recording...";
            
        } catch (err) {
            console.error("Microphone access denied:", err);
            alert("Please allow microphone access to use voice features.");
        }
    }

    function stopRecording() {
        if (mediaRecorder && isRecording) {
            mediaRecorder.stop();
            isRecording = false;
            
            voiceBtn.classList.add('bg-gray-100', 'dark:bg-gray-700', 'text-gray-600', 'dark:text-gray-300');
            voiceBtn.classList.remove('bg-red-500', 'text-white', 'pulse-recording');
            recordingStatus.classList.add('hidden');
            textInput.disabled = false;
            textInput.placeholder = "Type your question here...";
        }
    }

    function appendUserMessage(text, isTemporary = false) {
        const msgId = 'msg-' + Date.now();
        const html = `
            <div class="flex justify-end gap-4 max-w-[85%] self-end" id="${msgId}">
                <div class="bg-blue-600 p-4 rounded-2xl rounded-tr-none text-white shadow-sm text-sm">
                    ${text}
                </div>
                <div class="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center flex-shrink-0 mt-1">
                    <i class="fa-solid fa-user text-indigo-600 text-sm"></i>
                </div>
            </div>
        `;
        chatMessages.insertAdjacentHTML('beforeend', html);
        scrollToBottom();
        return msgId;
    }

    function updateUserMessage(msgId, newText) {
        const el = document.getElementById(msgId);
        if (el) el.querySelector('.bg-blue-600').innerHTML = newText;
    }

    function appendAIMessage(text) {
        const formattedText = text.replace(/\n/g, '<br>');
        const html = `
            <div class="flex gap-4 max-w-[85%]">
                <div class="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0 mt-1">
                    <i class="fa-solid fa-robot text-blue-600 text-sm"></i>
                </div>
                <div class="bg-gray-100 dark:bg-gray-700 p-4 rounded-2xl rounded-tl-none text-gray-800 dark:text-gray-200 shadow-sm text-sm">
                    ${formattedText}
                </div>
            </div>
        `;
        chatMessages.insertAdjacentHTML('beforeend', html);
        scrollToBottom();
    }

    function showLoading() {
        loadingIndicator.classList.remove('hidden');
        scrollToBottom();
    }

    function hideLoading() {
        loadingIndicator.classList.add('hidden');
    }

    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function playTTS(text) {
        if ('speechSynthesis' in window) {
            const msg = new SpeechSynthesisUtterance();
            msg.text = text.replace(/<[^>]*>?/gm, '');
            msg.lang = 'en-US';
            window.speechSynthesis.speak(msg);
        }
    }
}

// --- CONFIGURATION ---
const MAZE_LEVELS = [
    [ // Level 1
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 0, 0, 0, 1, 0, 0, 0, 2, 1],
        [1, 0, 1, 0, 1, 0, 1, 1, 1, 1],
        [1, 0, 1, 0, 0, 0, 0, 0, 0, 1],
        [1, 0, 1, 1, 1, 1, 1, 1, 0, 1],
        [1, 0, 0, 0, 0, 0, 1, 0, 0, 1],
        [1, 1, 1, 1, 1, 0, 1, 0, 1, 1],
        [1, 0, 0, 0, 1, 0, 0, 0, 0, 1],
        [1, 1, 1, 0, 1, 1, 1, 1, 0, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
    ],
    [ // Level 2
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
        [1, 0, 1, 1, 1, 0, 1, 0, 1, 1, 0, 1],
        [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1],
        [1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1],
        [1, 0, 1, 0, 0, 0, 0, 0, 0, 1, 2, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
    ],
    [ // Level 3
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 2, 1],
        [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1],
        [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1],
        [1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 0, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
        [1, 0, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
    ]
];

const DIFFICULTIES = {
    "Easy": { max_noticeable_dist: 6.0 },
    "Medium": { max_noticeable_dist: 4.5 },
    "Hard": { max_noticeable_dist: 3.0 }
};

// --- AUDIO SYSTEMS ---
const audioCtx = new (window.AudioContext || window.webkitAudioContext)();

function playTick() {
    if(audioCtx.state === 'suspended') audioCtx.resume();
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    
    osc.type = 'sine';
    osc.frequency.value = 880;
    
    gain.gain.setValueAtTime(1, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.03);
    
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    
    osc.start();
    osc.stop(audioCtx.currentTime + 0.05);
}

function speak(text) {
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.volume = 1;
    speechSynthesis.speak(utterance);
}

// --- STATE & UI DOM ---
let currentLevelIdx = 0;
let currentDifficulty = "Medium";
let recognizer = null;
let gameRunning = false;
let gameWon = false;
let lastTickTime = 0;

let player = { x: 0, y: 0, angle: 0 };
let activeMaze = [];

const menuView = document.getElementById('menu-view');
const gameView = document.getElementById('game-view');
const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');
const winOverlay = document.getElementById('win-overlay');

// UI Handlers Setup
document.querySelectorAll('#level-group .btn-toggle').forEach(btn => {
    btn.addEventListener('click', (e) => {
        document.querySelectorAll('#level-group .btn-toggle').forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        currentLevelIdx = parseInt(e.target.dataset.val);
        speak("Level " + (currentLevelIdx + 1));
    });
});

document.querySelectorAll('#diff-group .btn-toggle').forEach(btn => {
    btn.addEventListener('click', (e) => {
        document.querySelectorAll('#diff-group .btn-toggle').forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        currentDifficulty = e.target.dataset.val;
        speak(currentDifficulty);
    });
});

document.getElementById('btn-start').addEventListener('click', startGame);
document.getElementById('btn-quit').addEventListener('click', returnToMenu);
document.getElementById('btn-return').addEventListener('click', returnToMenu);

// --- VOICE CONTROL SYSTEM ---
document.getElementById('btn-voice-link').addEventListener('click', async () => {
    const statusDiv = document.getElementById('voice-status');
    const btn = document.getElementById('btn-voice-link');
    
    if (window.location.protocol === 'file:') {
        alert("Увага! Браузер блокує мікрофон для локальних файлів (file:///).\n\nВам необхідно відкрити гру через http://localhost:8000 або інший локальний сервер.");
        // continue anyway to let them see the exact error
    }

    btn.disabled = true;
    btn.innerText = "Loading Model...";
    statusDiv.classList.remove('hidden');
    statusDiv.style.color = "var(--neon-green)";
    statusDiv.innerText = "Downloading TFJS model...";

    try {
        let basePath = window.location.protocol === 'file:' ? 'http://127.0.0.1:8000/' : './';
        const URL = basePath + "tm-my-audio-model/";
        const checkpointURL = URL + "model.json";
        const metadataURL = URL + "metadata.json";

        recognizer = speechCommands.create("BROWSER_FFT", undefined, checkpointURL, metadataURL);
        await recognizer.ensureModelLoaded();
        
        statusDiv.innerText = "Model loaded! Requesting microphone...";
        const classLabels = recognizer.wordLabels();
        
        await recognizer.listen(result => {
            const scores = result.scores;
            let maxScore = 0;
            let maxIndex = 0;
            for (let i = 0; i < scores.length; i++) {
                if (scores[i] > maxScore) { maxScore = scores[i]; maxIndex = i; }
            }
            
            const command = classLabels[maxIndex];
            if (maxScore > 0.85 && command !== "Background Noise") {
                statusDiv.innerText = "Heard: " + command;
                if(gameRunning && !gameWon) {
                    executeCommand(command);
                }
            }
        }, {
            includeSpectrogram: false,
            probabilityThreshold: 0.85,
            invokeCallbackOnNoiseAndUnknown: false,
            overlapFactor: 0.50
        });
        
        statusDiv.innerText = "Listening for commands...";
        statusDiv.style.color = "var(--neon-green)";
        btn.innerText = "Microphone Linked";
        btn.classList.add("active");
        
    } catch(err) {
        console.error(err);
        statusDiv.style.color = "var(--danger)";
        statusDiv.innerText = "Error: " + err.message;
        btn.disabled = false;
        btn.innerText = "Try Again";
    }
});

// --- GAMEPLAY ENGINE ---
function startGame() {
    menuView.classList.add('hidden');
    gameView.classList.remove('hidden');
    winOverlay.classList.add('hidden');
    
    audioCtx.resume();
    activeMaze = MAZE_LEVELS[currentLevelIdx];
    
    // Find Start
    let found = false;
    for (let r = 0; r < activeMaze.length; r++) {
        for (let c = 0; c < activeMaze[0].length; c++) {
            if (activeMaze[r][c] === 0) {
                player.x = c + 0.5;
                player.y = r + 0.5;
                player.angle = 0;
                found = true; break;
            }
        }
        if (found) break;
    }
    
    gameRunning = true;
    gameWon = false;
    speak(`Start Level ${currentLevelIdx + 1}`);
    requestAnimationFrame(gameLoop);
}

function returnToMenu() {
    gameRunning = false;
    gameView.classList.add('hidden');
    menuView.classList.remove('hidden');
}

function castRay(px, py, angleDeg) {
    const angleRad = angleDeg * Math.PI / 180;
    const dx = Math.cos(angleRad);
    const dy = Math.sin(angleRad);
    
    const stepSize = 0.05;
    let distance = 0.0;
    const maxDist = 15.0;
    
    while (distance < maxDist) {
        distance += stepSize;
        let testX = Math.floor(px + dx * distance);
        let testY = Math.floor(py + dy * distance);
        
        if (testY < 0 || testY >= activeMaze.length || testX < 0 || testX >= activeMaze[0].length) {
            return distance;
        }
        if (activeMaze[testY][testX] === 1) {
            return distance;
        }
    }
    return maxDist;
}

function executeCommand(cmd) {
    if(cmd === "left") {
        player.angle -= 90;
        player.angle %= 360;
        if(player.angle < 0) player.angle += 360;
    } else if (cmd === "right") {
        player.angle += 90;
        player.angle %= 360;
    } else if (cmd === "up") { // forward W
        const rad = player.angle * Math.PI / 180;
        const nx = player.x + Math.round(Math.cos(rad));
        const ny = player.y + Math.round(Math.sin(rad));
        tryMove(nx, ny);
    } else if (cmd === "down") { // backward S
        const rad = player.angle * Math.PI / 180;
        const nx = player.x - Math.round(Math.cos(rad));
        const ny = player.y - Math.round(Math.sin(rad));
        tryMove(nx, ny);
    }
}

function tryMove(nx, ny) {
    const mapX = Math.floor(nx);
    const mapY = Math.floor(ny);
    
    if (mapY >= 0 && mapY < activeMaze.length && mapX >= 0 && mapX < activeMaze[0].length) {
        const cell = activeMaze[mapY][mapX];
        if (cell !== 1) {
            player.x = nx;
            player.y = ny;
            if (cell === 2) {
                gameWon = true;
                winOverlay.classList.remove('hidden');
                speak("CONGRATULATIONS");
            }
        }
    }
}

// Keyboard Mapping
window.addEventListener('keydown', e => {
    if(!gameRunning || gameWon) return;
    
    if (e.key === 'a' || e.key === 'A') executeCommand("left");
    if (e.key === 'd' || e.key === 'D') executeCommand("right");
    if (e.key === 'w' || e.key === 'W') executeCommand("up");
    if (e.key === 's' || e.key === 'S') executeCommand("down");
});

function gameLoop(timeMs) {
    if(!gameRunning) return;
    
    const maxDist = DIFFICULTIES[currentDifficulty].max_noticeable_dist;
    const dist = castRay(player.x, player.y, player.angle);
    
    // Tick Audio Logic
    if(!gameWon) {
        const minDelay = 0.05, maxDelay = 1.0;
        const normalized = Math.min(dist, maxDist) / maxDist;
        const tickDelaySeconds = minDelay + (maxDelay - minDelay) * normalized;
        
        const nowSec = timeMs / 1000;
        if (nowSec - lastTickTime >= tickDelaySeconds) {
            playTick();
            lastTickTime = nowSec;
        }
        
        document.getElementById('game-dist-info').innerText = `RADAR TRACE: ${dist.toFixed(1)}m`;
    }
    
    // Rendering
    drawGame(dist);
    requestAnimationFrame(gameLoop);
}

function drawGame(rayDist) {
    const cellSize = 40;
    const mapW = activeMaze[0].length * cellSize;
    const mapH = activeMaze.length * cellSize;
    const offsetX = (canvas.width - mapW) / 2;
    const offsetY = (canvas.height - mapH) / 2;
    
    ctx.fillStyle = '#050f05';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Draw cells
    for(let r=0; r<activeMaze.length; r++) {
        for(let c=0; c<activeMaze[0].length; c++) {
            const x = offsetX + c * cellSize;
            const y = offsetY + r * cellSize;
            
            if(activeMaze[r][c] === 1) {
                ctx.strokeStyle = '#00ff64';
                ctx.lineWidth = 1;
                ctx.strokeRect(x, y, cellSize, cellSize);
                ctx.fillStyle = '#0a280f';
                ctx.fillRect(x+1, y+1, cellSize-2, cellSize-2);
            } else if (activeMaze[r][c] === 2) {
                const pulse = Math.abs(Math.sin(Date.now() / 200)) * 155;
                ctx.fillStyle = `rgb(100, ${100 + pulse}, 100)`;
                ctx.fillRect(x, y, cellSize, cellSize);
            }
        }
    }
    
    const pxScreen = offsetX + player.x * cellSize;
    const pyScreen = offsetY + player.y * cellSize;
    
    if(!gameWon) {
        // Radar Cone
        ctx.fillStyle = 'rgba(0, 255, 100, 0.2)';
        ctx.beginPath();
        ctx.moveTo(pxScreen, pyScreen);
        const radCenter = player.angle * Math.PI / 180;
        const spread = 30 * Math.PI / 180;
        const radius = rayDist * cellSize;
        ctx.arc(pxScreen, pyScreen, radius, radCenter - spread/2, radCenter + spread/2);
        ctx.lineTo(pxScreen, pyScreen);
        ctx.fill();
        
        // Player dot
        ctx.beginPath();
        ctx.arc(pxScreen, pyScreen, 6, 0, 2*Math.PI);
        ctx.fillStyle = '#96ff96';
        ctx.fill();
        
        ctx.beginPath();
        ctx.arc(pxScreen, pyScreen, 10, 0, 2*Math.PI);
        ctx.strokeStyle = '#00ff64';
        ctx.lineWidth = 2;
        ctx.stroke();
    }
}

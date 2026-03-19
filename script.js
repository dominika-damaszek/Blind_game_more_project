// === CONFIGURATION ===
const LEVEL_CONFIGS = [
    { width: 11, height: 11, loopProb: 0.05 },  // Alpha
    { width: 15, height: 15, loopProb: 0.10 },  // Beta
    { width: 21, height: 21, loopProb: 0.15 }   // Gamma
];

const DIFFICULTIES = {
    "Easy":   { maxNoticeableDist: 6.0 },
    "Medium": { maxNoticeableDist: 4.5 },
    "Hard":   { maxNoticeableDist: 3.0 }
};

// === PROCEDURAL MAZE GENERATION (Randomized DFS) ===
function generateMaze(width, height, loopProb = 0) {
    if (width % 2 === 0) width++;
    if (height % 2 === 0) height++;

    const maze = Array.from({ length: height }, () => Array(width).fill(1));
    const dirs = [[0, -2], [0, 2], [-2, 0], [2, 0]];
    const distances = new Map();

    const inBounds = (x, y) => x > 0 && x < width - 1 && y > 0 && y < height - 1;

    maze[1][1] = 0;
    distances.set('1,1', 0);
    const stack = [[1, 1]];

    while (stack.length > 0) {
        const [ux, uy] = stack[stack.length - 1];
        const shuffled = [...dirs].sort(() => Math.random() - 0.5);
        let carved = false;

        for (const [dx, dy] of shuffled) {
            const nx = ux + dx, ny = uy + dy;
            if (inBounds(nx, ny) && maze[ny][nx] === 1) {
                maze[uy + dy / 2][ux + dx / 2] = 0;
                maze[ny][nx] = 0;
                const d = distances.get(`${ux},${uy}`) + 1;
                distances.set(`${nx},${ny}`, d);
                stack.push([nx, ny]);
                carved = true;
                break;
            }
        }
        if (!carved) stack.pop();
    }

    // Add loops
    for (let y = 1; y < height - 1; y++) {
        for (let x = 1; x < width - 1; x++) {
            if (maze[y][x] === 1 && Math.random() < loopProb) {
                const horiz = maze[y][x - 1] === 0 && maze[y][x + 1] === 0;
                const vert  = maze[y - 1][x] === 0 && maze[y + 1][x] === 0;
                if (horiz || vert) maze[y][x] = 0;
            }
        }
    }

    // Place goal at farthest cell from start
    let maxDist = 0, goalKey = '1,1';
    distances.forEach((d, k) => { if (d > maxDist) { maxDist = d; goalKey = k; } });
    const [gx, gy] = goalKey.split(',').map(Number);
    maze[gy][gx] = 2;

    return { maze, goalX: gx, goalY: gy };
}

// === AUDIO SYSTEM (Web Audio API) ===
const audioCtx = new (window.AudioContext || window.webkitAudioContext)();

function makeOscSound(freq, duration, decayRate, volume = 0.8) {
    return () => {
        if (audioCtx.state === 'suspended') audioCtx.resume();
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.type = 'sine';
        osc.frequency.value = freq;
        gain.gain.setValueAtTime(volume, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + duration);
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.start();
        osc.stop(audioCtx.currentTime + duration);
    };
}

const playThump = makeOscSound(80, 0.3, 15, 0.5);
const playSonarPing = makeOscSound(700, 0.2, 20, 0.25);

// Drone tone: continuous oscillator that changes pitch
let droneOsc = null, droneGain = null;
function startDrone(freq) {
    if (droneOsc) return; // already playing
    droneGain = audioCtx.createGain();
    droneGain.gain.setValueAtTime(0.12, audioCtx.currentTime);
    droneOsc = audioCtx.createOscillator();
    droneOsc.type = 'sine';
    droneOsc.frequency.setValueAtTime(freq, audioCtx.currentTime);
    droneOsc.connect(droneGain);
    droneGain.connect(audioCtx.destination);
    droneOsc.start();
}
function setDroneFreq(freq) {
    if (droneOsc) droneOsc.frequency.linearRampToValueAtTime(freq, audioCtx.currentTime + 0.1);
}
function stopDrone() {
    if (droneOsc) {
        droneGain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.2);
        droneOsc.stop(audioCtx.currentTime + 0.2);
        droneOsc = null; droneGain = null;
    }
}

// Spatial noise (left / right panning based on openings)
let noiseSource = null, noiseGainNode = null, pannerNode = null;

function startSpatialNoise() {
    if (noiseSource) return;
    const bufferSize = audioCtx.sampleRate * 0.5;
    const buffer = audioCtx.createBuffer(1, bufferSize, audioCtx.sampleRate);
    const data = buffer.getChannelData(0);
    // Low-pass filtered white noise for ambient rumble
    let last = 0;
    for (let i = 0; i < bufferSize; i++) {
        const white = Math.random() * 2 - 1;
        last = 0.95 * last + 0.05 * white;
        data[i] = last;
    }
    noiseSource = audioCtx.createBufferSource();
    noiseSource.buffer = buffer;
    noiseSource.loop = true;

    pannerNode = audioCtx.createStereoPanner();
    pannerNode.pan.value = 0;

    noiseGainNode = audioCtx.createGain();
    noiseGainNode.gain.value = 0;

    noiseSource.connect(noiseGainNode);
    noiseGainNode.connect(pannerNode);
    pannerNode.connect(audioCtx.destination);
    noiseSource.start();
}

function setSpatialNoise(volL, volR) {
    if (!noiseGainNode) return;
    
    // Add artificial wind gust oscillation
    const windGust = 0.6 + 0.4 * Math.sin(Date.now() / 1000 * 1.5);
    const finalVolL = volL * windGust;
    const finalVolR = volR * windGust;
    
    const totalVol = (finalVolL + finalVolR) / 2;
    const pan = finalVolR - finalVolL; // -1 = full left, +1 = full right
    noiseGainNode.gain.linearRampToValueAtTime(totalVol * 0.3, audioCtx.currentTime + 0.1);
    pannerNode.pan.linearRampToValueAtTime(Math.max(-1, Math.min(1, pan)), audioCtx.currentTime + 0.1);
}

function stopSpatialNoise() {
    if (noiseSource) {
        noiseGainNode.gain.setValueAtTime(0, audioCtx.currentTime);
        noiseSource.stop(audioCtx.currentTime + 0.1);
        noiseSource = null; noiseGainNode = null; pannerNode = null;
    }
}

// === TTS ACCESSIBILITY ===
const Voice = {
    timer: null,
    queueTimer: null,
    play: function(text, debounce = false) {
        if (!window.speechSynthesis) return;
        clearTimeout(this.timer);
        clearTimeout(this.queueTimer);
        
        const executeSpeak = (txt) => {
            window.speechSynthesis.cancel();
            // 50ms delay after cancel() prevents Windows native TTS buffer tearing
            setTimeout(() => {
                window._activeSynthUtterance = new SpeechSynthesisUtterance(", " + txt);
                window._activeSynthUtterance.volume = 0.8; 
                window._activeSynthUtterance.rate = 1.3;
                window.speechSynthesis.speak(window._activeSynthUtterance);
            }, 50);
        };

        if (!debounce) {
            // Buffer sync events (like focus + click hitting at the exact same ms)
            this.queueTimer = setTimeout(() => executeSpeak(text), 50);
        } else {
            this.timer = setTimeout(() => executeSpeak(text), 300);
        }
    },
    cancelHover: function() {
        clearTimeout(this.timer);
    }
};
function speak(text) { Voice.play(text, false); }

// === STATE ===
let currentLevelIdx = null;
let currentDifficulty = null;
let recognizer = null;
let gameRunning = false;
let gameWon = false;
let lastSonarTime = 0;
let blindMode = false;

let player = { x: 0, y: 0, angle: 0, visualX: 0, visualY: 0, visualAngle: 0 };
let activeMaze = [], goalX = 0, goalY = 0;

const hubView  = document.getElementById('hub-view');
const menuView = document.getElementById('menu-view');
const gameView = document.getElementById('game-view');
const canvas   = document.getElementById('gameCanvas');
const ctx      = canvas.getContext('2d');
const winOverlay = document.getElementById('win-overlay');
const dlOverlay  = document.getElementById('dl-overlay');

// === TTS HOVER AND WELCOME ===
let welcomed = false;
const hubWelcome = "Welcome to the Game Hub main menu. You are here. Your options to choose are: Play Audio Maze, Play Hand Puzzle game, or Download the code for those games.";

const initWelcome = () => {
    if (!welcomed) {
        speak(hubWelcome);
        welcomed = true;
    }
};

document.addEventListener('click', initWelcome);
document.addEventListener('keydown', initWelcome);

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('button, a.btn, h1, h2, p, .subtitle, .instruction').forEach(el => {
        const getTxt = () => {
            let baseTxt = el.getAttribute('aria-label') || el.textContent || el.innerText || "";
            let t = baseTxt.replace(/[\uD800-\uDBFF][\uDC00-\uDFFF]/g, '').trim();
            if (el.getAttribute('aria-disabled') === 'true') t += " (locked, select a difficulty first)";
            return t;
        };
        el.addEventListener('focus', () => Voice.play(getTxt(), false));
        el.addEventListener('mouseenter', () => Voice.play(getTxt(), false));
        el.addEventListener('mouseleave', () => Voice.cancelHover());
    });
});

// === UI SETUP ===
document.getElementById('btn-goto-maze').addEventListener('click', () => {
    currentLevelIdx = null; currentDifficulty = null;
    document.querySelectorAll('#level-group .btn-toggle').forEach(b => b.classList.remove('active'));
    document.getElementById('btn-voice-link').setAttribute('aria-disabled', 'true');
    document.getElementById('btn-blind-toggle').setAttribute('aria-disabled', 'true');
    document.getElementById('btn-start').setAttribute('aria-disabled', 'true');
    
    hubView.classList.add('hidden');
    menuView.classList.remove('hidden');
    speak("Audio Maze configuration opened. Please select a difficulty first.");
});

document.getElementById('btn-maze-tutorial').addEventListener('click', () => {
    speak("Tutorial. Wind sounds in your left or right ear indicate open paths. A beeping sonar gets faster as you approach the exit. A low thump means you hit a wall. Navigate using W A S D or voice commands to reach the goal.");
});

document.getElementById('btn-goto-puzzle').addEventListener('click', () => {
    speak("Loading Hand Puzzle.");
    setTimeout(() => { window.location.href = 'puzzle.html'; }, 300);
});

document.getElementById('btn-download-games').addEventListener('click', () => {
    dlOverlay.classList.remove('hidden');
    speak("Download menu opened.");
});

document.getElementById('btn-dl-close').addEventListener('click', () => {
    dlOverlay.classList.add('hidden');
    speak("Closed.");
});

document.getElementById('btn-back-hub').addEventListener('click', () => {
    menuView.classList.add('hidden');
    hubView.classList.remove('hidden');
    speak("Returned to Game Hub main menu. Options: Play Audio Maze, Play Hand Puzzle, or Download games.");
});

document.getElementById('btn-blind-toggle').addEventListener('click', e => {
    if (e.target.getAttribute('aria-disabled') === 'true') return;
    blindMode = !blindMode;
    e.target.innerText = "Blind: " + (blindMode ? "ON" : "OFF");
    e.target.classList.toggle('active', blindMode);
    speak("Blind mode is now " + (blindMode ? "ON" : "OFF"));
});

document.querySelectorAll('#level-group .btn-toggle').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('#level-group .btn-toggle').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentLevelIdx = parseInt(btn.dataset.val);
        const diffs = ["Easy", "Medium", "Hard"];
        currentDifficulty = diffs[currentLevelIdx];
        speak("Level " + currentDifficulty + " selected. Options unlocked.");
        
        document.getElementById('btn-voice-link').setAttribute('aria-disabled', 'false');
        document.getElementById('btn-blind-toggle').setAttribute('aria-disabled', 'false');
        document.getElementById('btn-start').setAttribute('aria-disabled', 'false');
    });
});
document.querySelectorAll('#diff-group .btn-toggle').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('#diff-group .btn-toggle').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentDifficulty = btn.dataset.val;
        const map = {"Easy": "level Easy", "Medium": "level Medium", "Hard": "level Hard"};
        speak(map[currentDifficulty]);
    });
});
document.getElementById('btn-start').addEventListener('click', startGame);
document.getElementById('btn-quit').addEventListener('click', returnToMenu);
document.getElementById('btn-return').addEventListener('click', returnToMenu);

// === VOICE CONTROL ===
document.getElementById('btn-voice-link').addEventListener('click', async () => {
    const btn = document.getElementById('btn-voice-link');
    if (btn.getAttribute('aria-disabled') === 'true') return;
    const statusDiv = document.getElementById('voice-status');

    btn.setAttribute('aria-disabled', 'true');
    btn.innerText = "Loading Model...";
    statusDiv.classList.remove('hidden');
    statusDiv.style.color = "var(--neon-green)";
    statusDiv.innerText = "Downloading TFJS model...";

    try {
        speak("Requesting microphone permission...");
        const modelBase = new URL('./tm-my-audio-model/', window.location.href).href;
        const cb = "?v=" + Date.now();
        const checkpointURL = modelBase + "model.json" + cb;
        const metadataURL   = modelBase + "metadata.json" + cb;

        recognizer = speechCommands.create("BROWSER_FFT", undefined, checkpointURL, metadataURL);
        await recognizer.ensureModelLoaded();

        statusDiv.innerText = "Requesting microphone...";
        const classLabels = recognizer.wordLabels();

        await recognizer.listen(result => {
            const scores = result.scores;
            let maxScore = 0, maxIndex = 0;
            scores.forEach((s, i) => { if (s > maxScore) { maxScore = s; maxIndex = i; } });
            const command = classLabels[maxIndex];
            if (maxScore > 0.85 && command !== "Background Noise") {
                document.getElementById('voice-status').innerText = "Heard: " + command;
                if (gameRunning && !gameWon) executeCommand(command);
            }
        }, { includeSpectrogram: false, probabilityThreshold: 0.85, invokeCallbackOnNoiseAndUnknown: false, overlapFactor: 0.50 });

        statusDiv.innerText = "Listening for commands...";
        btn.innerText = "Microphone Linked";
        btn.classList.add("active");

    } catch (err) {
        console.error(err);
        statusDiv.style.color = "var(--danger)";
        statusDiv.innerText = "Error: " + err.message;
        btn.disabled = false;
        btn.innerText = "Try Again";
    }
});

// === HELPERS ===
function angleToDirection(angle) {
    const a = ((Math.round(angle) % 360) + 360) % 360;
    if (a === 0)   return "East";
    if (a === 90)  return "South";
    if (a === 180) return "West";
    if (a === 270) return "North";
    return "";
}

function castRay(px, py, angleDeg) {
    const rad = angleDeg * Math.PI / 180;
    const dx = Math.cos(rad), dy = Math.sin(rad);
    const step = 0.05, maxDist = 15;
    let dist = 0;
    while (dist < maxDist) {
        dist += step;
        const tx = Math.floor(px + dx * dist);
        const ty = Math.floor(py + dy * dist);
        if (ty < 0 || ty >= activeMaze.length || tx < 0 || tx >= activeMaze[0].length) return dist;
        if (activeMaze[ty][tx] === 1) return dist;
    }
    return maxDist;
}

// === GAME START / STOP ===
function startGame() {
    if (document.getElementById('btn-start').getAttribute('aria-disabled') === 'true') return;
    audioCtx.resume();
    menuView.classList.add('hidden');
    gameView.classList.remove('hidden');
    winOverlay.classList.add('hidden');

    const cfg = LEVEL_CONFIGS[currentLevelIdx];
    const result = generateMaze(cfg.width, cfg.height, cfg.loopProb);
    activeMaze = result.maze;
    goalX = result.goalX + 0.5;
    goalY = result.goalY + 0.5;

    player.x = 1.5; player.y = 1.5; player.angle = 0;
    player.visualX = player.x; player.visualY = player.y; player.visualAngle = player.angle;

    gameRunning = true;
    gameWon = false;
    lastSonarTime = 0;
    droneOsc = null;

    startSpatialNoise();
    // Drone has been EXPERIMENTALLY DISABLED tracking updates
    // startDrone(50);

    const dx = goalX - player.x, dy = goalY - player.y;
    let dirStr = "";
    if (dy < -2) dirStr += "North ";
    else if (dy > 2) dirStr += "South ";
    if (dx > 2) dirStr += "East";
    else if (dx < -2) dirStr += "West";
    dirStr = dirStr.trim() || "Nearby";
    speak(`Start Level ${currentLevelIdx + 1}. Facing East. Goal is to the ${dirStr}.`);

    requestAnimationFrame(gameLoop);
}

function returnToMenu() {
    gameRunning = false;
    // stopDrone();
    stopSpatialNoise();
    gameView.classList.add('hidden');
    winOverlay.classList.add('hidden');
    menuView.classList.remove('hidden');
    speak("Game exited. Returned to Maze configuration.");
}

// === MOVEMENT ===
function tryMove(nx, ny) {
    const mx = Math.floor(nx), my = Math.floor(ny);
    if (my >= 0 && my < activeMaze.length && mx >= 0 && mx < activeMaze[0].length) {
        const cell = activeMaze[my][mx];
        if (cell !== 1) {
            player.x = nx; player.y = ny;
            if (cell === 2) {
                gameWon = true;
                stopDrone(); stopSpatialNoise();
                winOverlay.classList.remove('hidden');
                speak("CONGRATULATIONS! Exit reached!");
            }
        } else {
            playThump();
        }
    }
}

function executeCommand(cmd) {
    if (cmd === "left") {
        player.angle = ((player.angle - 90) + 360) % 360;
        const d = angleToDirection(player.angle); if (d) speak(d);
    } else if (cmd === "right") {
        player.angle = (player.angle + 90) % 360;
        const d = angleToDirection(player.angle); if (d) speak(d);
    } else if (cmd === "forward") {
        const rad = player.angle * Math.PI / 180;
        tryMove(player.x + Math.round(Math.cos(rad)), player.y + Math.round(Math.sin(rad)));
    } else if (cmd === "backward") {
        const rad = player.angle * Math.PI / 180;
        tryMove(player.x - Math.round(Math.cos(rad)), player.y - Math.round(Math.sin(rad)));
    }
}

window.addEventListener('keydown', e => {
    if (!gameRunning || gameWon) return;
    if (e.key === 'a' || e.key === 'A') executeCommand("left");
    if (e.key === 'd' || e.key === 'D') executeCommand("right");
    if (e.key === 'w' || e.key === 'W') executeCommand("forward");
    if (e.key === 's' || e.key === 'S') executeCommand("backward");
    if (e.key === 'Escape') returnToMenu();
    if (e.key === ' ' || e.code === 'Space') {
        e.preventDefault();
        const goalDist = Math.hypot(player.x - goalX, player.y - goalY).toFixed(1);
        const facing = angleToDirection(player.angle);
        const dx = goalX - player.x, dy = goalY - player.y;
        let dirStr = "";
        if (dy < -2) dirStr += "North ";
        else if (dy > 2) dirStr += "South ";
        if (dx > 2) dirStr += "East";
        else if (dx < -2) dirStr += "West";
        dirStr = dirStr.trim() || "Nearby";
        speak(`Facing ${facing}. Goal is to the ${dirStr}. Distance is ${goalDist} meters.`);
    }
});

// === GAME LOOP ===
let lastFrameTime = 0;

function gameLoop(timeMs) {
    if (!gameRunning) return;
    const dt = Math.min((timeMs - lastFrameTime) / 1000, 0.1);
    lastFrameTime = timeMs;

    const { maxNoticeableDist } = DIFFICULTIES[currentDifficulty];

    if (!gameWon) {
        // --- Front distance => drone tone (DISABLED as per Pygame sync) ---
        const distFront = castRay(player.x, player.y, player.angle);
        // const norm = Math.min(distFront, maxNoticeableDist) / maxNoticeableDist;
        // const freq = 50 + (1 - norm) * 200; // 50Hz (far) to 250Hz (close)
        // setDroneFreq(freq);
        document.getElementById('game-dist-info').innerText = blindMode ? "BLIND MODE ACTIVE" : `WALL: ${distFront.toFixed(1)}m`;

        // --- Spatial Audio (Left/Right openings) ---
        const distLeft  = castRay(player.x, player.y, player.angle - 90);
        const distRight = castRay(player.x, player.y, player.angle + 90);
        const threshold = 1.5;
        const volL = distLeft  > threshold ? Math.min(1, distLeft  / maxNoticeableDist) : 0;
        const volR = distRight > threshold ? Math.min(1, distRight / maxNoticeableDist) : 0;
        setSpatialNoise(volL, volR);

        // --- Sonar Ping (Goal proximity) ---
        const goalDist = Math.hypot(player.x - goalX, player.y - goalY);
        const pulseInterval = Math.max(0.2, Math.min(2.0, (goalDist / 15) * 1.8 + 0.2));
        if ((timeMs / 1000) - lastSonarTime > pulseInterval) {
            playSonarPing();
            lastSonarTime = timeMs / 1000;
        }
    }

    // --- Visual Lerp ---
    const lerpSpeed = Math.min(1, 12 * dt);
    player.visualX += (player.x - player.visualX) * lerpSpeed;
    player.visualY += (player.y - player.visualY) * lerpSpeed;
    let angleDiff = ((player.angle - player.visualAngle + 180 + 360) % 360) - 180;
    player.visualAngle += angleDiff * lerpSpeed;

    drawGame();
    requestAnimationFrame(gameLoop);
}

// === RENDERING (Player-centered, north-up rotated view) ===
function drawGame() {
    const CELL = 44;
    const cx = canvas.width / 2;
    const cy = canvas.height / 2;

    ctx.fillStyle = '#050f05';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // World rotated so player always faces UP on screen
    const worldAngle = (-90 - player.visualAngle) * Math.PI / 180;
    const cosA = Math.cos(worldAngle), sinA = Math.sin(worldAngle);

    const worldToScreen = (wx, wy) => {
        const dx = wx - player.visualX, dy = wy - player.visualY;
        return [cx + (dx * cosA - dy * sinA) * CELL, cy + (dx * sinA + dy * cosA) * CELL];
    };

    // Draw maze cells
    if (!blindMode) {
        for (let r = 0; r < activeMaze.length; r++) {
            for (let c = 0; c < activeMaze[0].length; c++) {
            const cell = activeMaze[r][c];
            if (cell === 0) continue;

            const pts = [
                worldToScreen(c,     r),
                worldToScreen(c + 1, r),
                worldToScreen(c + 1, r + 1),
                worldToScreen(c,     r + 1)
            ];
            ctx.beginPath();
            ctx.moveTo(...pts[0]);
            pts.slice(1).forEach(p => ctx.lineTo(...p));
            ctx.closePath();

            if (cell === 1) {
                ctx.fillStyle = '#0a2810';
                ctx.fill();
                ctx.strokeStyle = '#00ff64';
                ctx.lineWidth = 1;
                ctx.stroke();
            } else if (cell === 2) {
                const pulse = Math.abs(Math.sin(Date.now() / 200));
                const g = Math.floor(100 + pulse * 155);
                ctx.fillStyle = `rgb(100,${g},100)`;
                ctx.fill();
            }
        }
    }
    }

    if (!gameWon) {
        if (!blindMode) {
            // Radar cone pointing straight UP (player always faces up)
            const distFront = castRay(player.x, player.y, player.angle);
            const spread = 30 * Math.PI / 180;
            const UP = -Math.PI / 2;

            ctx.beginPath();
            ctx.moveTo(cx, cy);
            ctx.arc(cx, cy, distFront * CELL, UP - spread / 2, UP + spread / 2);
            ctx.lineTo(cx, cy);
            ctx.fillStyle = 'rgba(0, 255, 100, 0.18)';
            ctx.fill();
            ctx.strokeStyle = 'rgba(0, 255, 100, 0.5)';
            ctx.lineWidth = 1.5;
            ctx.stroke();

            // Player dot at center
            ctx.beginPath();
            ctx.arc(cx, cy, 6, 0, Math.PI * 2);
            ctx.fillStyle = '#96ff96';
            ctx.fill();
            ctx.beginPath();
            ctx.arc(cx, cy, 10, 0, Math.PI * 2);
            ctx.strokeStyle = '#00ff64';
            ctx.lineWidth = 2;
            ctx.stroke();

            // HUD
            const goalDist = Math.hypot(player.x - goalX, player.y - goalY);
            const facing = angleToDirection(player.angle);
            const font = ctx.font;
            ctx.font = '15px JetBrains Mono, monospace';
            ctx.fillStyle = '#00c850';
            ctx.fillText(`Wall: ${castRay(player.x, player.y, player.angle).toFixed(1)}m  Goal: ${goalDist.toFixed(1)}m  Facing: ${facing}`, 12, 24);
            ctx.font = font;
        } else {
            const font = ctx.font;
            ctx.font = '15px JetBrains Mono, monospace';
            ctx.fillStyle = '#0a3014';
            ctx.fillText(`ESC to Menu | BLIND MODE ACTIVE`, 12, 24);
            ctx.font = font;
        }
    }
}

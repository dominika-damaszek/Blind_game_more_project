// === CONFIGURATION ===
const WIN_W = 1100;
const WIN_H = 700;
const PUZZLE_RECT = { x: 400, y: 60, w: 640, h: 580 };
const CAMERA_RECT = { x: 20, y: 60, w: 360, h: 270 };
const PINCH_THRESH = 0.08;
const SNAP_FRACTION = 0.65;

const PALETTE = {
    bg: '#050f05', panel: '#0a2810', accent: '#00ff64',
    dim: '#006428', white: '#96ff96', danger: '#e65050', gold: '#00ff64'
};

// === UI ELEMENTS ===
const menuView = document.getElementById('menu-view');
const gameView = document.getElementById('game-view');
const winOverlay = document.getElementById('win-overlay');
const statusText = document.getElementById('status-text');
const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d', { willReadFrequently: true });
const videoElement = document.getElementById('input-video');

// === TTS ACCESSIBILITY ===
let welcomed = false;
const puzzleWelcome = "Welcome to the Hand Puzzle game main menu. You are here. Your options to choose are: Grid complexity Easy, Medium, or Hard. Then, Start Camera, or return to Hub.";

const Voice = {
    timer: null,
    queueTimer: null,
    play: function(text, debounce = false) {
        if (!window.speechSynthesis) return;
        clearTimeout(this.timer);
        clearTimeout(this.queueTimer);
        
        const executeSpeak = (txt) => {
            window.speechSynthesis.cancel();
            setTimeout(() => {
                window._activeSynthUtterance = new SpeechSynthesisUtterance(", " + txt);
                window._activeSynthUtterance.volume = 0.8; 
                window._activeSynthUtterance.rate = 1.3;
                window.speechSynthesis.speak(window._activeSynthUtterance);
            }, 50);
        };

        if (!debounce) {
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

const initWelcome = () => {
    if (!welcomed) {
        speak(puzzleWelcome);
        welcomed = true;
    }
};

document.addEventListener('click', initWelcome);
document.addEventListener('keydown', initWelcome);

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('button, a.btn, h1, h2, p, .subtitle, .instruction').forEach(el => {
        const getTxt = () => {
            let baseTxt = el.getAttribute('aria-label') || el.textContent || el.innerText || "";
            return baseTxt.replace(/[\uD800-\uDBFF][\uDC00-\uDFFF]/g, '').trim();
        };
        el.addEventListener('focus', () => Voice.play(getTxt(), false));
        el.addEventListener('mouseenter', () => Voice.play(getTxt(), false));
        el.addEventListener('mouseleave', () => Voice.cancelHover());
    });
});

let currentDiff = 5;
document.querySelectorAll('.btn-toggle').forEach(b => {
    b.addEventListener('click', () => {
        document.querySelectorAll('.btn-toggle').forEach(btn => btn.classList.remove('active'));
        b.classList.add('active');
        currentDiff = parseInt(b.dataset.val);
        AudioEngine.click();
        
        let diffStr = currentDiff === 5 ? "level Easy" : (currentDiff === 10 ? "level Medium" : "level Hard");
        speak(diffStr);
    });
});
document.getElementById('btn-return').addEventListener('click', () => {
    AudioEngine.stopBGM();
    winOverlay.classList.add('hidden');
    gameState = 'menu';
    gameView.classList.add('hidden');
    menuView.classList.remove('hidden');
    speak("Returned to Hand Puzzle main menu. Options are: Grid complexities, Start Camera, or Hub.");
});

// Exit button
document.getElementById('btn-quit').addEventListener('click', () => {
    AudioEngine.stopBGM();
    gameState = 'menu';
    gameView.classList.add('hidden');
    menuView.classList.remove('hidden');
    speak("Game exited. Returned to Hand Puzzle main menu. Options are: Grid complexities, Start Camera, or Hub.");
});

// Hub button
document.getElementById('btn-goto-hub').addEventListener('click', () => {
    AudioEngine.stopBGM();
    speak("Returning to Game Hub.");
    setTimeout(() => { window.location.href = 'index.html'; }, 300);
});

// === PROCEDURAL AUDIO ===
const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
const AudioEngine = {
    synth: function(freqStart, freqEnd, duration, type, vol) {
        if (audioCtx.state === 'suspended') audioCtx.resume();
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.type = type;
        osc.frequency.setValueAtTime(freqStart, audioCtx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(freqEnd, audioCtx.currentTime + duration);
        gain.gain.setValueAtTime(vol, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + duration);
        osc.connect(gain); gain.connect(audioCtx.destination);
        osc.start(); osc.stop(audioCtx.currentTime + duration);
    },
    click:   () => AudioEngine.synth(1200, 400, 0.1, 'sine', 0.2),
    hover:   () => AudioEngine.synth(800, 800, 0.05, 'sine', 0.05),
    shutter: () => AudioEngine.synth(800, 200, 0.15, 'square', 0.15),
    grab:    () => AudioEngine.synth(300, 600, 0.1, 'sine', 0.1),
    snap:    () => AudioEngine.synth(800, 1200, 0.15, 'sine', 0.2),
    error:   () => AudioEngine.synth(200, 100, 0.2, 'sawtooth', 0.1),
    win:     () => {
        setTimeout(() => AudioEngine.synth(400, 400, 0.15, 'sine', 0.2), 0);
        setTimeout(() => AudioEngine.synth(500, 500, 0.15, 'sine', 0.2), 150);
        setTimeout(() => AudioEngine.synth(600, 800, 0.40, 'sine', 0.3), 300);
    },
    bgmTimer: null,
    startBGM: function() {
        if (this.bgmTimer) return;
        const notes = [220, 261.63, 329.63, 392.00];
        let step = 0;
        const playNote = () => {
            if (audioCtx.state === 'suspended') audioCtx.resume();
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();
            const filter = audioCtx.createBiquadFilter();
            
            const freq = notes[step % notes.length] * (Math.random() > 0.8 ? 0.5 : 1);
            osc.type = 'sine';
            osc.frequency.value = freq;
            
            filter.type = 'lowpass';
            filter.frequency.value = 600;

            gain.gain.setValueAtTime(0, audioCtx.currentTime);
            gain.gain.linearRampToValueAtTime(0.015, audioCtx.currentTime + 1);
            gain.gain.linearRampToValueAtTime(0, audioCtx.currentTime + 3);
            
            osc.connect(filter);
            filter.connect(gain);
            gain.connect(audioCtx.destination);
            
            osc.start();
            osc.stop(audioCtx.currentTime + 3);
            
            step++;
            this.bgmTimer = setTimeout(playNote, 2000);
        };
        playNote();
    },
    stopBGM: function() {
        clearTimeout(this.bgmTimer);
        this.bgmTimer = null;
    }
};

// === GAME STATE ===
let gameState = 'menu'; // menu, capture, puzzle
let puzzleState = null;
let rawFrame = null;    // Captured webcam frame for rendering

// Capture mode vars
let isCapturing = false;
let captureStart = 0;
const captureDuration = 1.5;
let screenFlash = 0.0;

// Cursor Smoothing
class CursorFilter {
    constructor() { this.cursors = {}; this.alpha = 0.4; }
    update(hands) {
        let incoming = [];
        let keys = Object.keys(this.cursors);
        
        hands.forEach(h => {
            let px = h.ix * WIN_W, py = h.iy * WIN_H;
            let bestK = null, bestDist = 9999;
            for (let k of keys) {
                let d = Math.hypot(this.cursors[k].x - px, this.cursors[k].y - py);
                if (d < 150 && d < bestDist) { bestK = k; bestDist = d; }
            }
            if (bestK) {
                keys = keys.filter(k => k !== bestK);
                let c = this.cursors[bestK];
                c.x = c.x * (1 - this.alpha) + px * this.alpha;
                c.y = c.y * (1 - this.alpha) + py * this.alpha;
                c.pinch = h.pinch;
                incoming.push(c);
            } else {
                let id = Math.random().toString();
                let nc = { id, x: px, y: py, pinch: h.pinch, smoothPinch: 0 };
                this.cursors[id] = nc;
                incoming.push(nc);
            }
        });
        
        this.cursors = {};
        incoming.forEach(c => {
            let target = c.pinch ? 1.0 : 0.0;
            c.smoothPinch += (target - c.smoothPinch) * 0.3;
            this.cursors[c.id] = c;
        });
        return Object.values(this.cursors);
    }
}
const cursorFilter = new CursorFilter();
let activeCursors = [];

// === PUZZLE LOGIC ===
class Tile {
    constructor(cx, cy, cw, ch, imgData, sourceX, sourceY) {
        this.cx = cx; this.cy = cy; this.cw = cw; this.ch = ch;
        this.x = cx; this.y = cy;
        this.img = imgData;
        this.sx = sourceX; this.sy = sourceY;
        this.locked = false;
        this.beingHeld = false;
        this.ox = 0; this.oy = 0;
        this.scale = 1.0;
    }
}

class Puzzle {
    constructor(videoCanvas, rect, gridN) {
        this.tiles = [];
        this.gridN = gridN;
        this.tw = rect.w / gridN;
        this.th = rect.h / gridN;
        this.particles = [];
        this.heldTile = null;

        // Create a scaled snapshot of the video frame
        const snap = document.createElement('canvas');
        snap.width = rect.w; snap.height = rect.h;
        const sCtx = snap.getContext('2d');
        sCtx.drawImage(videoCanvas, 0, 0, rect.w, rect.h);

        let positions = [];
        for (let r = 0; r < gridN; r++) {
            for (let c = 0; c < gridN; c++) {
                let cx = rect.x + c * this.tw, cy = Math.floor(rect.y + r * this.th);
                positions.push({ x: cx, y: cy });
                this.tiles.push(new Tile(cx, cy, this.tw, this.th, snap, c * this.tw, r * this.th));
            }
        }
        
        // Shuffle positions
        positions.sort(() => Math.random() - 0.5);
        this.tiles.forEach((t, i) => { t.x = positions[i].x; t.y = positions[i].y; });
    }
    
    get solved() { return this.tiles.every(t => t.locked); }

    addParticles(x, y, count=15) {
        for (let i=0; i<count; i++) {
            this.particles.push({
                x, y, vx: (Math.random()-0.5)*8, vy: Math.random()*-4,
                r: Math.random()*3+3, life: 1.0
            });
        }
    }

    grab(px, py) {
        if (this.heldTile) return false;
        for (let i = this.tiles.length - 1; i >= 0; i--) {
            let t = this.tiles[i];
            if (!t.locked && px > t.x && px < t.x+t.cw && py > t.y && py < t.y+t.ch) {
                this.heldTile = t;
                t.beingHeld = true;
                t.ox = t.x - px; t.oy = t.y - py;
                AudioEngine.grab();
                return true;
            }
        }
        return false;
    }

    move(px, py) {
        if (this.heldTile) {
            this.heldTile.x = px + this.heldTile.ox;
            this.heldTile.y = py + this.heldTile.oy;
        }
    }

    release() {
        if (!this.heldTile) return;
        let t = this.heldTile;
        let dx = Math.abs((t.x + t.cw/2) - (t.cx + t.cw/2));
        let dy = Math.abs((t.y + t.ch/2) - (t.cy + t.ch/2));
        if (dx < t.cw * SNAP_FRACTION && dy < t.ch * SNAP_FRACTION) {
            t.x = t.cx; t.y = t.cy;
            t.locked = true;
            AudioEngine.snap();
            this.addParticles(t.x + t.cw/2, t.y + t.ch/2);
        } else {
            AudioEngine.error();
        }
        t.beingHeld = false;
        this.heldTile = null;
    }

    draw() {
        // bg slots
        ctx.strokeStyle = PALETTE.bg; ctx.lineWidth = 2;
        for (let r = 0; r < this.gridN; r++) {
            for (let c = 0; c < this.gridN; c++) {
                ctx.fillStyle = PALETTE.panel;
                ctx.fillRect(PUZZLE_RECT.x + c * this.tw, PUZZLE_RECT.y + r * this.th, this.tw, this.th);
                ctx.strokeRect(PUZZLE_RECT.x + c * this.tw, PUZZLE_RECT.y + r * this.th, this.tw, this.th);
            }
        }
        // highlight snap
        if (this.heldTile) {
            let t = this.heldTile;
            let dx = Math.abs((t.x + t.cw/2) - (t.cx + t.cw/2));
            let dy = Math.abs((t.y + t.ch/2) - (t.cy + t.ch/2));
            if (dx < t.cw * SNAP_FRACTION && dy < t.ch * SNAP_FRACTION) {
                ctx.fillStyle = 'rgba(20, 220, 160, 0.2)';
                ctx.fillRect(t.cx, t.cy, t.cw, t.ch);
                ctx.strokeStyle = PALETTE.accent; ctx.lineWidth = 4;
                ctx.strokeRect(t.cx, t.cy, t.cw, t.ch);
            }
        }
        
        // basic tiles
        this.tiles.forEach(t => {
            if (t.beingHeld) return;
            if (!t.locked) {
                ctx.fillStyle = '#000'; ctx.fillRect(t.x+3, t.y+3, t.cw, t.ch);
            }
            ctx.drawImage(t.img, t.sx, t.sy, t.cw, t.ch, t.x, t.y, t.cw, t.ch);
            if (!t.locked) { ctx.strokeStyle = PALETTE.dim; ctx.lineWidth = 2; ctx.strokeRect(t.x, t.y, t.cw, t.ch); }
        });
        
        // held tile
        if (this.heldTile) {
            let t = this.heldTile;
            t.scale += (1.1 - t.scale) * 0.2;
            let ext = (t.scale - 1.0) * t.cw;
            let hx = t.x - ext/2, hy = t.y - ext/2, hw = t.cw + ext, hh = t.ch + ext;
            ctx.fillStyle = 'rgba(0,0,0,0.5)'; ctx.fillRect(hx+8, hy+12, hw, hh);
            ctx.drawImage(t.img, t.sx, t.sy, t.cw, t.ch, hx, hy, hw, hh);
            ctx.strokeStyle = PALETTE.gold; ctx.lineWidth = 4; ctx.strokeRect(hx, hy, hw, hh);
        }

        // particles
        for (let i = this.particles.length - 1; i >= 0; i--) {
            let p = this.particles[i];
            p.x += p.vx; p.y += p.vy; p.vy += 0.2; p.life -= 0.03;
            if (p.life <= 0) { this.particles.splice(i, 1); continue; }
            ctx.beginPath(); ctx.arc(p.x, p.y, p.r * p.life, 0, Math.PI*2);
            ctx.fillStyle = PALETTE.accent; ctx.fill();
        }
    }
}

// === RENDER LOOP ===
function drawCursors() {
    activeCursors.forEach(c => {
        let r = 16 - (c.smoothPinch * 6);
        if (c.smoothPinch > 0.8) {
            let p = (Math.sin(Date.now()/50)+1)*3;
            ctx.beginPath(); ctx.arc(c.x, c.y, r + 8 + p, 0, Math.PI*2);
            ctx.strokeStyle = PALETTE.gold; ctx.lineWidth = 2; ctx.stroke();
        }
        ctx.beginPath(); ctx.arc(c.x, c.y, r, 0, Math.PI*2);
        ctx.fillStyle = c.smoothPinch > 0.5 ? PALETTE.gold : PALETTE.white;
        ctx.fill();
        ctx.strokeStyle = PALETTE.bg; ctx.lineWidth = 2; ctx.stroke();
    });
}

function gameLoop() {
    ctx.fillStyle = PALETTE.bg;
    ctx.fillRect(0, 0, WIN_W, WIN_H);

    if (screenFlash > 0) {
        ctx.fillStyle = `rgba(255,255,255,${screenFlash})`;
        ctx.fillRect(0, 0, WIN_W, WIN_H);
        screenFlash -= 0.1;
    }

    if (gameState === 'capture') {
        if (rawFrame) {
            ctx.drawImage(rawFrame, 0, 0, WIN_W, WIN_H);
        }
        ctx.fillStyle = 'rgba(10, 15, 20, 0.8)';
        ctx.fillRect(0, 0, WIN_W, 90);
        ctx.fillStyle = PALETTE.accent; ctx.font = 'bold 22px Courier'; ctx.textAlign = 'center';
        ctx.fillText("Point BOTH index fingers to frame your photo.", WIN_W/2, 35);
        ctx.fillStyle = PALETTE.white; ctx.font = '16px Courier';
        ctx.fillText("PINCH & HOLD to start the capture timer!", WIN_W/2, 70);

        let anyPinch = activeCursors.some(c => c.pinch);
        if (activeCursors.length >= 2) {
            let p1 = activeCursors[0], p2 = activeCursors[1];
            let rx = Math.min(p1.x, p2.x), ry = Math.min(p1.y, p2.y);
            let rw = Math.max(Math.abs(p2.x - p1.x), 10), rh = Math.max(Math.abs(p2.y - p1.y), 10);
            
            if (anyPinch) {
                if (!isCapturing) { isCapturing = true; captureStart = Date.now(); }
                let prog = (Date.now() - captureStart) / (captureDuration * 1000);
                
                ctx.strokeStyle = '#ff6432'; ctx.lineWidth = 4;
                ctx.strokeRect(rx, ry, rw, rh);
                
                let cx2 = rx + rw/2, cy2 = ry + rh/2;
                ctx.beginPath();
                ctx.arc(cx2, cy2, 40, -Math.PI/2, -Math.PI/2 + prog * 2 * Math.PI);
                ctx.strokeStyle = '#ff6432'; ctx.lineWidth = 10; ctx.stroke();
                
                ctx.fillStyle = '#ff6432'; ctx.font = 'bold 32px Courier';
                ctx.fillText(Math.ceil(captureDuration - prog*captureDuration), cx2, cy2+10);

                if (prog >= 1.0 && rw > 40) {
                    AudioEngine.shutter();
                    screenFlash = 1.0;
                    
                    // Create crop canvas
                    const cropCanvas = document.createElement('canvas');
                    cropCanvas.width = rw; cropCanvas.height = rh;
                    cropCanvas.getContext('2d').drawImage(rawFrame, rx, ry, rw, rh, 0, 0, rw, rh);
                    
                    puzzleState = new Puzzle(cropCanvas, PUZZLE_RECT, currentDiff);
                    gameState = 'puzzle';
                    isCapturing = false;
                    
                    const quitBox = document.getElementById('quit-box');
                    quitBox.style.top = '72.5%';
                    quitBox.style.left = '3.6%';
                    quitBox.style.right = 'auto';
                    quitBox.style.width = '29.1%';
                }
            } else {
                isCapturing = false;
                ctx.strokeStyle = PALETTE.accent; ctx.lineWidth = 3;
                ctx.strokeRect(rx, ry, rw, rh);
            }
            [p1, p2].forEach(p => {
                ctx.beginPath(); ctx.arc(p.x, p.y, 5, 0, Math.PI*2);
                ctx.fillStyle = PALETTE.white; ctx.fill();
            });
        } else {
            isCapturing = false;
            ctx.fillStyle = PALETTE.danger; ctx.font = 'bold 22px Courier'; ctx.textAlign = 'center';
            ctx.fillText(activeCursors.length === 0 ? "Show BOTH hands!" : "Waiting for OTHER hand...", WIN_W/2, WIN_H - 80);
        }
    } else if (gameState === 'puzzle') {
        if (rawFrame) {
            ctx.drawImage(rawFrame, CAMERA_RECT.x, CAMERA_RECT.y, CAMERA_RECT.w, CAMERA_RECT.h);
            ctx.strokeStyle = PALETTE.dim; ctx.lineWidth = 2;
            ctx.strokeRect(CAMERA_RECT.x, CAMERA_RECT.y, CAMERA_RECT.w, CAMERA_RECT.h);
        }
        
        ctx.fillStyle = PALETTE.panel;
        ctx.fillRect(20, 360, 360, 235);
        ctx.strokeStyle = PALETTE.dim; ctx.strokeRect(20, 360, 360, 235);
        
        let sc = puzzleState.tiles.filter(t => t.locked).length;
        let tc = puzzleState.tiles.length;
        ctx.fillStyle = PALETTE.white; ctx.font = 'bold 22px Courier'; ctx.textAlign = 'left';
        ctx.fillText(`Progress: ${sc}/${tc}`, 40, 395);
        
        ctx.fillStyle = PALETTE.bg; ctx.fillRect(40, 415, 320, 12);
        ctx.fillStyle = PALETTE.accent; ctx.fillRect(40, 415, 320 * (sc/tc), 12);

        ctx.fillStyle = PALETTE.dim; ctx.font = '16px Courier';
        ctx.fillText("PINCH & HOLD to grab tiles", 40, 455);
        ctx.fillText("Snap them into glowing slots", 40, 477);
        
        puzzleState.draw();

        // Logic
        let maxPinch = 0; let bestC = null;
        activeCursors.forEach(c => {
            if (c.smoothPinch > 0.8) {
                if (!puzzleState.heldTile) puzzleState.grab(c.x, c.y);
            } else {
                if (puzzleState.heldTile) puzzleState.release();
            }
            if (c.smoothPinch > maxPinch) { maxPinch = c.smoothPinch; bestC = c; }
        });
        
        if (puzzleState.heldTile && bestC) {
            puzzleState.move(bestC.x, bestC.y);
        }

        if (puzzleState.solved) {
            AudioEngine.stopBGM();
            gameState = 'menu'; // logic ends, win screen shows
            AudioEngine.win();
            winOverlay.classList.remove('hidden');
            speak("Puzzle solved! Reconstruction complete.");
        }
    }

    if (gameState !== 'menu') drawCursors();
    requestAnimationFrame(gameLoop);
}

// === MEDIAPIPE INIT ===
const hands = new Hands({locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`});
hands.setOptions({ maxNumHands: 2, modelComplexity: 1, minDetectionConfidence: 0.6, minTrackingConfidence: 0.6 });

const snapshotCanvas = document.createElement('canvas');
const sCtx = snapshotCanvas.getContext('2d');
snapshotCanvas.width = WIN_W; snapshotCanvas.height = WIN_H;

hands.onResults(results => {
    // Save image
    sCtx.save();
    sCtx.scale(-1, 1);
    sCtx.drawImage(results.image, -WIN_W, 0, WIN_W, WIN_H);
    sCtx.restore();
    rawFrame = snapshotCanvas;

    let hData = [];
    if (results.multiHandLandmarks) {
        results.multiHandLandmarks.forEach(lm => {
            let ix = 1 - lm[8].x, iy = lm[8].y; // Mirrored
            let tx = 1 - lm[4].x, ty = lm[4].y;
            let pinch = Math.hypot(ix - tx, iy - ty) < PINCH_THRESH;
            hData.push({ ix, iy, pinch });
        });
    }
    activeCursors = cursorFilter.update(hData);
});

document.getElementById('btn-start').addEventListener('click', async () => {
    audioCtx.resume();
    AudioEngine.click();
    AudioEngine.startBGM();
    menuView.classList.add('hidden');
    gameView.classList.remove('hidden');
    statusText.classList.remove('hidden');
    speak("Camera active. Please point your computer to both of your hands.");
    
    // Reset Exit Button Position
    const quitBox = document.getElementById('quit-box');
    quitBox.style.top = '15px';
    quitBox.style.right = '15px';
    quitBox.style.left = 'auto';
    quitBox.style.width = 'auto';
    
    // Start Camera
    const camera = new Camera(videoElement, {
        onFrame: async () => { await hands.send({image: videoElement}); },
        width: 640, height: 480
    });
    camera.start().then(() => {
        statusText.classList.add('hidden');
        gameState = 'capture';
        requestAnimationFrame(gameLoop);
    });
});

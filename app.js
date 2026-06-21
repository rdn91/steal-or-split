let ws;
let username;
let callFrame;
const DAILY_ROOM_URL = "https://rdn91.daily.co/split-or-steal-room"

function startVideoCall () {
    const videoContainer = document.getElementById("video-container")

    callFrame = DailyIframe.createFrame(videoContainer, {
        iframeStyle: {
            width: "100%",
            height: "100%",
            border: "0"
        },
        showLeaveButton: false,
        showFullscreenButton: true
    });

    callFrame.join({ url: DAILY_ROOM_URL });
}

function handleServerMessage(data) {
    switch(data.type) {
        case "waiting":
            document.getElementById('status-text').innerText = "Waiting for an opponent...";
            break;
        case "match_found":
            document.getElementById("status-text").innerText = "Match Found! Connecting..."
            setTimeout(() => {
                transtitionTogameScreen(data.objective);
            }, 1000);
            break;
        case "timer_update":
            document.getElementById("timer").innerText = data.seconds + "s"
        case "phase_lockin":
            document.getElementById("timer").innerText = "LOCK IN";
            document.getElementById("split-button").disabled = false;
            document.getElementById("steal-button").disabled = false;
            break;
        case "game_over":
            handleGameOver(data);
            break;
    }       
}

function transtitionTogameScreen(objectiveText) {
    document.getElementById('lobby-screen').classList.add("hidden");
    document.getElementById("game-screen").classList.remove("hidden");

    document.getElementById('player-identity').innerText = "Identity" + username;
    document.getElementById("private-objective").innerText = "Objective" + objective;

    startVideoCall()
}

function startMatchMaking() {
    const usernameInput = document.getElementById("username-input");
    username = usernameInput.value.trim();
    
    if (!username) {
        alert("Please enter a username first");
        return;
    }

    ws = new WebSocket(`ws://localhost:8000/ws/matchmaking/${encodeURIComponent(username)}`);

    ws.onmessage = function(event) {
        const data = JSON.parse(event.data);
        handleServerMessage(data);
    }
}

function submitDecision(choice) {
    document.getElementById("split-button").disabled = true;
    document.getElementById("steal-button").disabled = true;

    const payload = {
        type: "decision_submit",
        choice : choice
    };
    ws.send(JSON.stringify(payload))
}

function handleGameOver(data) {
    if (callFrame) {
        callFrame.leave();
    }
    alert(`GAME OVER\n\nYou Chose: ${data.your_choice}\nOpponent chose: ${data.opponent_choice}\n\nResult: ${data.outcome}`);
    location.reload();
}

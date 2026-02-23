const Input = {
  mouse: {
    left: false,
    middle: false,
    right: false
  }
};

function updateUI() {
  document.getElementById("left").innerText = Input.mouse.left;
  document.getElementById("middle").innerText = Input.mouse.middle;
  document.getElementById("right").innerText = Input.mouse.right;
}

document.addEventListener("mousedown", (event) => {
  if (event.button === 0) Input.mouse.left = true;
  if (event.button === 1) Input.mouse.middle = true;
  if (event.button === 2) Input.mouse.right = true;
  updateUI();
});

document.addEventListener("mouseup", (event) => {
  if (event.button === 0) Input.mouse.left = false;
  if (event.button === 1) Input.mouse.middle = false;
  if (event.button === 2) Input.mouse.right = false;
  updateUI();
});

// Right-click menu disable
document.addEventListener("contextmenu", e => e.preventDefault());
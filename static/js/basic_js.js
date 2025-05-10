document.addEventListener('DOMContentLoaded', function () {
document.querySelectorAll('.btn-close').forEach(function (btn) {
  btn.addEventListener('click', function () {
    const alert = btn.closest('.alert');
    if (alert) {
      alert.classList.remove('show');
      setTimeout(() => {
        alert.remove();
      }, 150); // Delay for fade-out animation (optional)
    }
  });
});

  // Auto-hide alerts after 5 seconds
setTimeout(() => {
    document.querySelectorAll('.alerts').forEach(alerts => {
      alerts.classList.remove('shows');
      setTimeout(() => alerts.remove(), 150);
    });
  }, 2500);
});


function toggleVisibility(inputId, iconElement) {
  const input = document.getElementById(inputId);
  if (input.type === "password") {
    input.type = "text";
    iconElement.textContent = "👁️";
  } else {
    input.type = "password";
    iconElement.textContent = "🙈";
  }
}

window.addEventListener('pageshow', function (event) {
  if (event.persisted || window.performance && window.performance.navigation.type === 2) {
      window.location.reload();
  }
});

let showMore = false;
function toggleColumns() {
  const moreCols = document.querySelectorAll('.more-col');
  moreCols.forEach(col => {
    col.style.display = showMore ? 'none' : 'table-cell';
  });

  const btn = document.querySelector('button');
  btn.textContent = showMore ? 'Show More' : 'Show Less';
  showMore = !showMore;
}


// frontend/assets/js/login.js

// Limpiar mensaje de error al cargar la página
window.addEventListener('DOMContentLoaded', () => {
  const errorMessage = document.getElementById('errorMessage');
  if (errorMessage) errorMessage.textContent = '';
});

document.getElementById('loginForm').addEventListener('submit', async function (e) {
  e.preventDefault();

  const username = document.getElementById('username').value.trim();
  const errorMessage = document.getElementById('errorMessage');

  // Validación básica del lado cliente
  if (!username.endsWith('@udistrital.edu.co')) {
    errorMessage.style.color = 'red';
    errorMessage.textContent = 'Ingresar un correo válido de @udistrital.edu.co';
    return;
  }

  try {
    const response = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username })
    });
    const data = await response.json();

    if (response.ok) {
      // Guardar estado de autenticación
      localStorage.setItem('auth', 'true');
      localStorage.setItem('user', username);

      errorMessage.style.color = '#004080'; // Azul para éxito
      errorMessage.textContent = data.message;

      setTimeout(() => {
        window.location.href = '/principal.html';
      }, 500);
    } else {
      errorMessage.style.color = 'red';
      errorMessage.textContent = data.detail;
    }
  } catch (err) {
    console.error(err);
    errorMessage.style.color = 'red';
    errorMessage.textContent = 'Error de conexión con el servidor';
  }
});

function toggleAdminLogin() {
    const usernameField = document.getElementById('username');
    const passwordField = document.getElementById('password');
    const loginButton = document.getElementById('login-btn');
    const toggleAdminLink = document.getElementById('toggle-admin-link');
    const createAccountLink = document.getElementById('create-account-link');

    if (loginButton.textContent === "Login") {
        // Switch to Admin Login
        loginButton.textContent = "Admin Login";
        usernameField.placeholder = "Admin Username";
        passwordField.placeholder = "Admin Password";
        toggleAdminLink.textContent = "Switch to User Login";
        createAccountLink.style.display = "none";
    } else {
        // Switch to User Login
        loginButton.textContent = "Login";
        usernameField.placeholder = "Username";
        passwordField.placeholder = "Password";
        toggleAdminLink.textContent = "Switch to Admin Login";
        createAccountLink.style.display = "block";
    }
}

function showAccountCreationForm() {
    document.getElementById('login-form').style.display = 'none';
    document.getElementById('account-creation-form').style.display = 'block';
}

function showLoginForm() {
    document.getElementById('account-creation-form').style.display = 'none';
    document.getElementById('login-form').style.display = 'block';
}
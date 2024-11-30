// Script used in login
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

// Script used in cart
document.querySelectorAll('.image-button').forEach(button => {
    button.addEventListener('click', (event) => {
        const action = event.target.closest('button').getAttribute('data-action');
        const itemId = event.target.closest('button').getAttribute('data-item-id');
        
        
        fetch('/update_cart', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                item_id: itemId,
                action: action
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
      
                document.getElementById(`quantity-${itemId}`).textContent = data.new_quantity;
                document.getElementById('total-price').textContent = data.new_total_price;
            } else {
                alert('Error updating cart');
            }
        });
    });
});

// Script used in Checkout
var acc = document.getElementsByClassName("accordion");
        for (var i = 0; i < acc.length; i++) {
            acc[i].addEventListener("click", function() {
                this.classList.toggle("active");
                var panel = this.nextElementSibling;
                if (panel.style.display === "block") {
                    panel.style.display = "none";
                } else {
                    panel.style.display = "block";
                }
            });
        }
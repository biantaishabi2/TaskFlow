// Main JavaScript file

document.addEventListener('DOMContentLoaded', function() {
    console.log('Flask application loaded successfully');
    
    // Add current year to footer
    const footerYear = document.querySelector('footer p');
    if (footerYear) {
        footerYear.innerHTML = footerYear.innerHTML.replace('{{ now.year }}', new Date().getFullYear());
    }
    
    // Add active class to current navigation link
    const currentLocation = window.location.pathname;
    const navLinks = document.querySelectorAll('nav ul li a');
    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentLocation) {
            link.parentElement.classList.add('active');
        }
    });
});

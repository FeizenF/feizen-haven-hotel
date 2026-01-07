// JavaScript khusus untuk index.html

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize AOS
    if (typeof AOS !== 'undefined') {
        AOS.init({
            duration: 800,
            once: true,
            offset: 100
        });
    }

    // Form submission for contact form
    const contactForm = document.getElementById('contactForm');
    if (contactForm) {
        contactForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Get form values
            const name = this.querySelector('input[type="text"]').value;
            const email = this.querySelector('input[type="email"]').value;
            
            // Validate form
            if (!name || !email) {
                alert('Please fill in all required fields');
                return;
            }
            
            // Show success message
            alert(`Thank you for your inquiry, ${name}! We will contact you shortly at ${email}.`);
            
            // Reset form
            this.reset();
        });
    }

    // Auto-hide navbar on scroll down
    let lastScrollTop = 0;
    const navbar = document.getElementById('navbar');
    
    if (navbar) {
        window.addEventListener('scroll', () => {
            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
            if (scrollTop > lastScrollTop && scrollTop > 100) {
                // Scrolling down
                navbar.style.transform = 'translateY(-100%)';
            } else {
                // Scrolling up
                navbar.style.transform = 'translateY(0)';
            }
            lastScrollTop = scrollTop;
        });
    }

    // Update active nav link based on scroll
    const navLinks = document.querySelectorAll('.nav-link');
    
    function updateActiveNavLink() {
        const sections = document.querySelectorAll('section');
        let current = '';
        
        sections.forEach(section => {
            const sectionTop = section.offsetTop;
            const sectionHeight = section.clientHeight;
            if (window.scrollY >= sectionTop - 150) {
                current = section.getAttribute('id');
            }
        });
        
        navLinks.forEach(link => {
            link.classList.remove('active', 'text-gold');
            if (link.getAttribute('href') === `#${current}`) {
                link.classList.add('active', 'text-gold');
            }
        });
    }

    // Check URL hash on page load
    const hash = window.location.hash;
    if (hash) {
        setTimeout(() => {
            const target = document.querySelector(hash);
            if (target) {
                window.scrollTo({
                    top: target.offsetTop - 80,
                    behavior: 'smooth'
                });
            }
        }, 100);
    }

    // Listen for scroll to update active nav link
    window.addEventListener('scroll', updateActiveNavLink);
});
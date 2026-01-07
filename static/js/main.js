// ===== main.js - ENHANCED VERSION =====

// ===== CONFIGURATION =====
const CONFIG = {
    debug: false,
    scrollThreshold: 20,
    transitionDuration: 300,
    dropdownTransition: 200
};

// ===== UTILITY FUNCTIONS =====
const utils = {
    log: function(...args) {
        if (CONFIG.debug) {
            console.log('[Feizen Haven]', ...args);
        }
    },
    
    error: function(...args) {
        console.error('[Feizen Haven Error]', ...args);
    },
    
    debounce: function(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },
    
    showNotification: function(message, type = 'info', duration = 3000) {
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 p-4 rounded-lg shadow-lg z-50 animate-fadeInDown ${this.getNotificationColor(type)}`;
        notification.innerHTML = `
            <div class="flex items-center">
                <i class="fas ${this.getNotificationIcon(type)} mr-3"></i>
                <div>
                    <p class="font-medium">${message}</p>
                </div>
                <button class="ml-4 text-gray-500 hover:text-gray-700" onclick="this.parentElement.parentElement.remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remove after duration
        setTimeout(() => {
            if (notification.parentNode) {
                notification.style.opacity = '0';
                notification.style.transform = 'translateY(-10px)';
                notification.style.transition = 'opacity 0.3s, transform 0.3s';
                setTimeout(() => {
                    if (notification.parentNode) {
                        notification.parentNode.removeChild(notification);
                    }
                }, 300);
            }
        }, duration);
    },
    
    getNotificationColor: function(type) {
        const colors = {
            error: 'bg-red-100 text-red-800 border-l-4 border-red-500',
            success: 'bg-green-100 text-green-800 border-l-4 border-green-500',
            warning: 'bg-yellow-100 text-yellow-800 border-l-4 border-yellow-500',
            info: 'bg-blue-100 text-blue-800 border-l-4 border-blue-500'
        };
        return colors[type] || colors.info;
    },
    
    getNotificationIcon: function(type) {
        const icons = {
            error: 'fa-exclamation-circle',
            success: 'fa-check-circle',
            warning: 'fa-exclamation-triangle',
            info: 'fa-info-circle'
        };
        return icons[type] || icons.info;
    },
    
    resetFormButton: function(button, originalText) {
        if (button) {
            button.disabled = false;
            button.innerHTML = originalText;
        }
    }
};

// ===== AUTO-HIDE NOTIFICATIONS =====
function setupAutoHideNotifications() {
    const notifications = document.querySelectorAll('.alert, .flash-message, .notification');
    
    notifications.forEach(notification => {
        // Auto-hide after 3 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                notification.style.opacity = '0';
                notification.style.transform = 'translateY(-10px)';
                
                setTimeout(() => {
                    if (notification.parentNode) {
                        notification.parentNode.removeChild(notification);
                    }
                }, 300);
            }
        }, 3000);
        
        // Manual close
        const closeBtn = notification.querySelector('.close-btn, .alert-close, [data-dismiss="alert"]');
        if (closeBtn) {
            closeBtn.addEventListener('click', function() {
                notification.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                notification.style.opacity = '0';
                notification.style.transform = 'translateY(-10px)';
                
                setTimeout(() => {
                    if (notification.parentNode) {
                        notification.parentNode.removeChild(notification);
                    }
                }, 300);
            });
        }
    });
}

// ===== FORM SUBMISSION PROTECTION =====
function setupFormSubmissionProtection() {
    const forms = document.querySelectorAll('form[method="POST"]:not([data-no-protection])');
    
    forms.forEach(form => {
        let isSubmitting = false;
        let submitButton = form.querySelector('button[type="submit"]');
        let originalButtonText = submitButton ? submitButton.innerHTML : '';
        
        form.addEventListener('submit', function(e) {
            if (isSubmitting) {
                e.preventDefault();
                return;
            }
            
            // Validate required fields
            const requiredFields = this.querySelectorAll('[required]');
            let isValid = true;
            let firstInvalidField = null;
            
            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    isValid = false;
                    if (!firstInvalidField) {
                        firstInvalidField = field;
                    }
                    field.classList.add('border-red-500');
                    
                    // Remove red border after user types
                    field.addEventListener('input', function() {
                        this.classList.remove('border-red-500');
                    }, { once: true });
                }
            });
            
            if (!isValid) {
                e.preventDefault();
                if (firstInvalidField) {
                    firstInvalidField.focus();
                }
                utils.showNotification('Please fill in all required fields.', 'error');
                return;
            }
            
            isSubmitting = true;
            
            // Disable submit button
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Processing...';
            }
            
            // Reset button state if form submission fails
            this.addEventListener('ajax:error', function() {
                isSubmitting = false;
                utils.resetFormButton(submitButton, originalButtonText);
            });
            
            // Also reset on page unload (in case user navigates away)
            window.addEventListener('beforeunload', function() {
                isSubmitting = false;
                if (submitButton) {
                    submitButton.disabled = false;
                    submitButton.innerHTML = originalButtonText;
                }
            });
        });
        
        // Reset button state when form is reset
        form.addEventListener('reset', function() {
            isSubmitting = false;
            utils.resetFormButton(submitButton, originalButtonText);
        });
    });
}

// ===== PAYMENT FORM SPECIFIC HANDLING =====
function setupPaymentForm() {
    const paymentForm = document.getElementById('paymentForm');
    if (!paymentForm) return;
    
    let isSubmitting = false;
    const submitButton = paymentForm.querySelector('button[type="submit"]');
    const originalButtonText = submitButton ? submitButton.innerHTML : '';
    
    paymentForm.addEventListener('submit', function(e) {
        if (isSubmitting) {
            e.preventDefault();
            return;
        }
        
        // Get selected payment method
        const selectedMethod = this.querySelector('input[name="payment_method"]');
        if (!selectedMethod || !selectedMethod.value) {
            e.preventDefault();
            utils.showNotification('Please select a payment method.', 'error');
            return;
        }
        
        // For non-QRIS methods, check file upload
        if (selectedMethod.value !== 'qris') {
            const fileInput = this.querySelector('input[name="payment_proof"]');
            if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
                e.preventDefault();
                utils.showNotification(`Please upload payment proof for ${selectedMethod.value.toUpperCase()} payment.`, 'error');
                return;
            }
            
            // Validate file
            const file = fileInput.files[0];
            const validTypes = ['image/jpeg', 'image/png', 'image/jpg', 'application/pdf'];
            const maxSize = 5 * 1024 * 1024;
            
            if (!validTypes.includes(file.type)) {
                e.preventDefault();
                utils.showNotification('Please upload a JPG, PNG, or PDF file.', 'error');
                isSubmitting = false;
                utils.resetFormButton(submitButton, originalButtonText);
                return;
            }
            
            if (file.size > maxSize) {
                e.preventDefault();
                utils.showNotification('File size must be less than 5MB.', 'error');
                isSubmitting = false;
                utils.resetFormButton(submitButton, originalButtonText);
                return;
            }
        }
        
        isSubmitting = true;
        
        // Show loading state
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Processing...';
        }
        
        // Add a safety timeout to reset button if form takes too long
        const safetyTimeout = setTimeout(() => {
            if (isSubmitting) {
                console.warn('Form submission taking too long, resetting button');
                isSubmitting = false;
                utils.resetFormButton(submitButton, originalButtonText);
            }
        }, 10000); // 10 second timeout
        
        // Clear timeout when form actually submits
        this.addEventListener('submit', function() {
            clearTimeout(safetyTimeout);
        }, { once: true });
    });
}

// ===== PREVENT BROWSER BACK BUTTON =====
function setupBackButtonPrevention() {
    if (window.location.pathname.includes('/payment') || 
        window.location.pathname.includes('/booking/')) {
        
        // Replace history state to prevent back navigation
        window.history.replaceState(null, null, window.location.href);
        window.history.pushState(null, null, window.location.href);
        
        window.addEventListener('popstate', function(event) {
            const confirmLeave = confirm(
                'Are you sure you want to leave? Your payment will be cancelled.'
            );
            
            if (confirmLeave) {
                window.location.href = '/rooms';
            } else {
                window.history.pushState(null, null, window.location.href);
            }
        });
    }
}

// ===== INITIALIZE EVERYTHING (Enhanced) =====
function initApp() {
    utils.log('🚀 Initializing Feizen Haven application...');
    
    try {
        // Make page visible
        document.body.style.opacity = '1';
        document.body.style.visibility = 'visible';
        
        setTimeout(() => {
            document.body.classList.add('initialized');
        }, 50);
        
        // Setup notifications first
        setupAutoHideNotifications();
        
        // Core functionality
        setupNavbarScroll();
        setupMobileMenu();
        setupSmoothScroll();
        initUserDropdown();
        
        // Form handling
        setupFormSubmissionProtection();
        setupPaymentForm();
        setupFormHelpers();
        
        // Back button prevention
        setupBackButtonPrevention();
        
        // Enhanced features
        setupLazyLoading();
        setupHomeLinks();
        
        utils.log('✅ All components initialized successfully');
        
    } catch (error) {
        utils.error('Failed to initialize application:', error);
        
        // Fallback
        document.body.style.opacity = '1';
        document.body.style.visibility = 'visible';
        document.body.classList.add('initialized');
    }
}

// ===== USER DROPDOWN =====
function initUserDropdown() {
    const dropdownButton = document.getElementById('userDropdownButton');
    const dropdownMenu = document.getElementById('userDropdownMenu');
    
    if (!dropdownButton || !dropdownMenu) return;
    
    function showDropdown() {
        dropdownMenu.classList.add('show');
        dropdownMenu.style.opacity = '0';
        dropdownMenu.style.transform = 'translateY(-10px)';
        
        setTimeout(() => {
            dropdownMenu.style.opacity = '1';
            dropdownMenu.style.transform = 'translateY(0)';
            dropdownMenu.style.transition = `opacity ${CONFIG.dropdownTransition}ms ease, transform ${CONFIG.dropdownTransition}ms ease`;
        }, 10);
        
        const arrow = dropdownButton.querySelector('.fa-chevron-down');
        if (arrow) {
            arrow.style.transform = 'rotate(180deg)';
            arrow.style.transition = 'transform 0.3s ease';
        }
    }
    
    function hideDropdown() {
        dropdownMenu.style.opacity = '0';
        dropdownMenu.style.transform = 'translateY(-10px)';
        
        setTimeout(() => {
            dropdownMenu.classList.remove('show');
        }, CONFIG.dropdownTransition);
        
        const arrow = dropdownButton.querySelector('.fa-chevron-down');
        if (arrow) {
            arrow.style.transform = 'rotate(0deg)';
        }
    }
    
    dropdownButton.addEventListener('click', function(e) {
        e.stopPropagation();
        e.preventDefault();
        
        dropdownMenu.classList.contains('show') ? hideDropdown() : showDropdown();
    });
    
    document.addEventListener('click', function(e) {
        if (dropdownMenu.classList.contains('show') && 
            !dropdownButton.contains(e.target) && 
            !dropdownMenu.contains(e.target)) {
            hideDropdown();
        }
    });
    
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && dropdownMenu.classList.contains('show')) {
            hideDropdown();
        }
    });
}

// ===== MOBILE MENU =====
function setupMobileMenu() {
    const menuToggle = document.getElementById('menuToggle');
    const mobileMenu = document.getElementById('mobileMenu');
    
    if (!menuToggle || !mobileMenu) return;
    
    menuToggle.addEventListener('click', function(e) {
        e.stopPropagation();
        mobileMenu.classList.toggle('hidden');
        
        const icon = this.querySelector('svg');
        if (icon) {
            icon.innerHTML = mobileMenu.classList.contains('hidden') 
                ? '<path d="M4 6h16M4 12h16M4 18h16"/>'
                : '<path d="M6 18L18 6M6 6l12 12"/>';
        }
    });
    
    document.addEventListener('click', function(event) {
        if (!mobileMenu.classList.contains('hidden') &&
            !menuToggle.contains(event.target) &&
            !mobileMenu.contains(event.target)) {
            mobileMenu.classList.add('hidden');
            
            const icon = menuToggle.querySelector('svg');
            if (icon) {
                icon.innerHTML = '<path d="M4 6h16M4 12h16M4 18h16"/>';
            }
        }
    });
    
    mobileMenu.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', () => {
            mobileMenu.classList.add('hidden');
            
            const icon = menuToggle.querySelector('svg');
            if (icon) {
                icon.innerHTML = '<path d="M4 6h16M4 12h16M4 18h16"/>';
            }
        });
    });
}

// ===== NAVBAR SCROLL EFFECT =====
function setupNavbarScroll() {
    const navbar = document.getElementById('navbar');
    if (!navbar) return;
    
    const updateNavbarOnScroll = utils.debounce(function() {
        if (window.scrollY > CONFIG.scrollThreshold) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
    }, 10);
    
    window.addEventListener('scroll', updateNavbarOnScroll);
    updateNavbarOnScroll();
}

// ===== SMOOTH SCROLLING =====
function setupSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const targetId = this.getAttribute('href');
            
            if (targetId === '#' || targetId === '') return;
            
            if (targetId.startsWith('#') && targetId.length > 1) {
                e.preventDefault();
                const targetElement = document.querySelector(targetId);
                
                if (targetElement) {
                    const navbarHeight = document.getElementById('navbar')?.offsetHeight || 80;
                    const offsetTop = targetElement.offsetTop - navbarHeight;
                    
                    window.scrollTo({
                        top: offsetTop,
                        behavior: 'smooth'
                    });
                    
                    history.pushState(null, null, targetId);
                    
                    const mobileMenu = document.getElementById('mobileMenu');
                    if (mobileMenu && !mobileMenu.classList.contains('hidden')) {
                        mobileMenu.classList.add('hidden');
                        
                        const menuToggle = document.getElementById('menuToggle');
                        if (menuToggle) {
                            const icon = menuToggle.querySelector('svg');
                            if (icon) {
                                icon.innerHTML = '<path d="M4 6h16M4 12h16M4 18h16"/>';
                            }
                        }
                    }
                }
            }
        });
    });
}

// ===== FORM HELPERS =====
function setupFormHelpers() {
    // Auto-focus first input
    document.querySelectorAll('form').forEach(form => {
        const firstInput = form.querySelector('input:not([type="hidden"]), textarea, select');
        if (firstInput && !firstInput.value) {
            firstInput.focus();
        }
    });
    
    // Password toggle
    document.querySelectorAll('.password-toggle').forEach(toggle => {
        toggle.addEventListener('click', function() {
            const input = this.previousElementSibling;
            if (input && input.type === 'password') {
                input.type = 'text';
                this.innerHTML = '<i class="fas fa-eye-slash"></i>';
            } else if (input) {
                input.type = 'password';
                this.innerHTML = '<i class="fas fa-eye"></i>';
            }
        });
    });
}

// ===== LAZY LOADING =====
function setupLazyLoading() {
    if ('IntersectionObserver' in window) {
        const lazyImages = document.querySelectorAll('img[data-src]');
        
        const imageObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.classList.add('loaded');
                    imageObserver.unobserve(img);
                }
            });
        });
        
        lazyImages.forEach(img => imageObserver.observe(img));
    }
}

// ===== HOME CLICK HANDLER =====
function handleHomeClick(event) {
    const currentPath = window.location.pathname;
    const homePath = '/';
    
    if (currentPath === homePath || currentPath === '/index' || currentPath === '/home') {
        event.preventDefault();
        event.stopPropagation();
        
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
        
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
        });
        event.target.classList.add('active');
        
        return false;
    }
    
    return true;
}

function setupHomeLinks() {
    document.querySelectorAll('a[href="/"], a[href*="index"]').forEach(link => {
        link.addEventListener('click', handleHomeClick);
    });
}

// ===== ERROR HANDLING =====
window.addEventListener('error', function(e) {
    utils.error('Global error caught:', e.message, e.filename, e.lineno);
});

// ===== PAGE VISIBILITY =====
document.addEventListener('visibilitychange', function() {
    if (!document.hidden) {
        utils.log('Page became visible');
    }
});

// ===== INITIALIZATION =====
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
} else {
    initApp();
}

// Export for debugging
if (CONFIG.debug) {
    window.FeizenHaven = {
        utils,
        initApp,
        initUserDropdown,
        setupMobileMenu,
        setupNavbarScroll,
        setupSmoothScroll
    };
    utils.log('Debug mode enabled');
}
// ===== PAYMENT FORM SPECIFIC HANDLING =====
function setupPaymentForm() {
    const paymentForm = document.getElementById('paymentForm');
    if (!paymentForm) return;
    
    let isSubmitting = false;
    const submitButton = paymentForm.querySelector('button[type="submit"]');
    const originalButtonText = submitButton ? submitButton.innerHTML : '';
    const universalUploadSection = document.getElementById('universalUploadSection');
    
    // Show upload section when payment method is selected
    paymentForm.addEventListener('change', function(e) {
        if (e.target.name === 'payment_method' && e.target.value) {
            if (universalUploadSection) {
                universalUploadSection.classList.remove('hidden');
            }
        }
    });
    
    paymentForm.addEventListener('submit', function(e) {
        if (isSubmitting) {
            e.preventDefault();
            return;
        }
        
        // Get selected payment method
        const selectedMethod = this.querySelector('input[name="payment_method"]');
        if (!selectedMethod || !selectedMethod.value) {
            e.preventDefault();
            utils.showNotification('Please select a payment method.', 'error');
            return;
        }
        
        // Validate file upload for ALL methods including QRIS
        const fileInput = this.querySelector('input[name="payment_proof"]');
        if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
            e.preventDefault();
            utils.showNotification(`Please upload payment proof for ${selectedMethod.value.toUpperCase()} payment.`, 'error');
            return;
        }
        
        // Validate file
        const file = fileInput.files[0];
        const validTypes = ['image/jpeg', 'image/png', 'image/jpg', 'application/pdf'];
        const maxSize = 5 * 1024 * 1024;
        
        if (!validTypes.includes(file.type)) {
            e.preventDefault();
            utils.showNotification('Please upload a JPG, PNG, or PDF file.', 'error');
            isSubmitting = false;
            utils.resetFormButton(submitButton, originalButtonText);
            return;
        }
        
        if (file.size > maxSize) {
            e.preventDefault();
            utils.showNotification('File size must be less than 5MB.', 'error');
            isSubmitting = false;
            utils.resetFormButton(submitButton, originalButtonText);
            return;
        }
        
        isSubmitting = true;
        
        // Show loading state
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Processing...';
        }
        
        // Safety timeout
        const safetyTimeout = setTimeout(() => {
            if (isSubmitting) {
                console.warn('Form submission taking too long, resetting button');
                isSubmitting = false;
                utils.resetFormButton(submitButton, originalButtonText);
            }
        }, 10000);
        
        this.addEventListener('submit', function() {
            clearTimeout(safetyTimeout);
        }, { once: true });
    });
}
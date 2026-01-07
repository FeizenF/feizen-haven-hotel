
let currentStep = 1;
let selectedRoom = 'executive';
let selectedPaymentMethod = 'qris';

const roomData = {
    'deluxe': {
        name: 'Deluxe Room',
        price: 1500000,
        description: '35 m² • City View • Sleeps 2'
    },
    'executive': {
        name: 'Executive Suite',
        price: 3000000,
        description: '60 m² • Mountain View • Sleeps 3'
    },
    'presidential': {
        name: 'Presidential Suite',
        price: 7500000,
        description: '120 m² • Panoramic View • Sleeps 4'
    }
};

function selectPaymentMethod(method) {
    selectedPaymentMethod = method;
    
    document.querySelectorAll('.payment-method').forEach(pm => {
        pm.classList.remove('selected');
    });
    
    const selectedElement = document.querySelector(`.payment-method[data-method="${method}"]`);
    if (selectedElement) {
        selectedElement.classList.add('selected');
    }
    
    const selectedPaymentInput = document.getElementById('selectedPaymentMethod');
    if (selectedPaymentInput) {
        selectedPaymentInput.value = method;
    }
    

    const finalPaymentElement = document.getElementById('final-payment');
    if (finalPaymentElement) {
        finalPaymentElement.textContent = method.toUpperCase();
    }
}

function setupRoomSelection() {
    const roomOptions = document.querySelectorAll('.room-option');
    
    roomOptions.forEach(option => {
        option.addEventListener('click', function() {
   
            roomOptions.forEach(opt => opt.classList.remove('selected'));
            

            this.classList.add('selected');
            

            selectedRoom = this.getAttribute('data-room');
            

            updateBookingSummary();
        });
    });
}

function formatRupiah(amount) {
    return 'Rp' + amount.toLocaleString('id-ID');
}


function updateBookingSummary() {
    const room = roomData[selectedRoom];
    const nights = 2; ghts
    
    if (!room) return;
    
    const roomCharges = room.price * nights;
    const taxService = Math.round(roomCharges * 0.11);
    const total = roomCharges + taxService;
    
    const summaryRoom = document.getElementById('summary-room');
    const summaryPrice = document.getElementById('summary-price');
    const summaryCharges = document.getElementById('summary-charges');
    const summaryTax = document.getElementById('summary-tax');
    const summaryTotal = document.getElementById('summary-total');
    const finalRoom = document.getElementById('final-room');
    const finalTotal = document.getElementById('final-total');
    
    if (summaryRoom) summaryRoom.textContent = room.name;
    if (summaryPrice) summaryPrice.textContent = formatRupiah(room.price);
    if (summaryCharges) summaryCharges.textContent = formatRupiah(roomCharges);
    if (summaryTax) summaryTax.textContent = formatRupiah(taxService);
    if (summaryTotal) summaryTotal.textContent = formatRupiah(total);
    

    if (finalRoom) finalRoom.textContent = room.name;
    if (finalTotal) finalTotal.textContent = formatRupiah(total);
}


function goToStep(step) {

    document.querySelectorAll('section').forEach(section => {
        section.classList.remove('section-active');
        section.classList.add('section-hidden');
    });
    
    const targetSection = document.getElementById(
        step === 1 ? 'facilities-view' : 
        step === 2 ? 'rooms-selection' : 
        'booking-form'
    );
    
    if (targetSection) {
        targetSection.classList.remove('section-hidden');
        targetSection.classList.add('section-active');
        
        document.querySelectorAll('.progress-step').forEach((stepEl, index) => {
            stepEl.classList.remove('active', 'completed');
            
            if (index + 1 < step) {
                stepEl.classList.add('completed');
            } else if (index + 1 === step) {
                stepEl.classList.add('active');
            }
        });
        
        const progressBar = document.getElementById('progress-bar');
        if (progressBar) {
            progressBar.style.width = `${(step/3)*100}%`;
        }
        
        currentStep = step;
        
        window.scrollTo({
            top: targetSection.offsetTop - 100,
            behavior: 'smooth'
        });
    }
}
function showPopup() {
    const popup = document.getElementById('bookingPopup');
    if (popup) {
        popup.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

function closePopup() {
    const popup = document.getElementById('bookingPopup');
    if (popup) {
        popup.classList.remove('active');
        document.body.style.overflow = ''; 
    }
}

function goToHome() {
    closePopup();
    window.location.href = 'index.html';
}

function generateBookingId() {
    const prefix = 'FH-2025-';
    const randomNum = Math.floor(100000 + Math.random() * 900000);
    return prefix + randomNum;
}

function formatDisplayDate(dateStr) {
    if (!dateStr) return '--/--/----';
    
    try {
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-GB', {
            day: 'numeric',
            month: 'short',
            year: 'numeric'
        });
    } catch (e) {
        return dateStr;
    }
}

function submitBooking() {

    const termsCheckbox = document.getElementById('final-terms');
    if (termsCheckbox && !termsCheckbox.checked) {
        alert('Please agree to the terms and conditions');
        termsCheckbox.focus();
        return;
    }
    
    if (!selectedPaymentMethod) {
        alert('Please select a payment method');
        return;
    }
    
    const firstName = document.getElementById('firstName')?.value;
    const lastName = document.getElementById('lastName')?.value;
    const email = document.getElementById('email')?.value;
    const phone = document.getElementById('phone')?.value;
    const checkin = document.getElementById('final-checkin')?.value;
    const checkout = document.getElementById('final-checkout')?.value;
    const guests = document.getElementById('guests')?.value;
    
    if (!firstName || !lastName || !email || !phone || !checkin || !checkout) {
        alert('Please fill in all required fields');
        return;
    }
    
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        alert('Please enter a valid email address');
        document.getElementById('email')?.focus();
        return;
    }
    
    if (phone.length < 10) {
        alert('Please enter a valid phone number');
        document.getElementById('phone')?.focus();
        return;
    }
    
    const checkinDate = new Date(checkin);
    const checkoutDate = new Date(checkout);
    if (checkinDate >= checkoutDate) {
        alert('Check-out date must be after check-in date');
        return;
    }
    
    const roomName = roomData[selectedRoom]?.name || 'Executive Suite';
    const totalElement = document.getElementById('final-total');
    const total = totalElement ? totalElement.textContent : 'Rp6,660,000';
    const bookingId = generateBookingId();
    
    const popupBookingId = document.getElementById('popupBookingId');
    const popupRoom = document.getElementById('popupRoom');
    const popupCheckin = document.getElementById('popupCheckin');
    const popupCheckout = document.getElementById('popupCheckout');
    const popupGuests = document.getElementById('popupGuests');
    const popupTotal = document.getElementById('popupTotal');
    
    if (popupBookingId) popupBookingId.textContent = bookingId;
    if (popupRoom) popupRoom.textContent = roomName;
    if (popupCheckin) popupCheckin.textContent = formatDisplayDate(checkin);
    if (popupCheckout) popupCheckout.textContent = formatDisplayDate(checkout);
    if (popupGuests) popupGuests.textContent = guests + (guests == 1 ? ' Guest' : ' Guests');
    if (popupTotal) popupTotal.textContent = total;
    
    showPopup();
}


function initializeDates() {
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 2);
    
    function formatDate(date) {
        return date.toISOString().split('T')[0];
    }
    
    const checkinInput = document.getElementById('final-checkin');
    const checkoutInput = document.getElementById('final-checkout');
    const checkinDisplay = document.getElementById('final-checkin-display');
    const checkoutDisplay = document.getElementById('final-checkout-display');
    
    if (checkinInput) {
        checkinInput.value = formatDate(today);
        checkinInput.min = formatDate(today);
    }
    
    if (checkoutInput) {
        checkoutInput.value = formatDate(tomorrow);
    }
    
    if (checkinDisplay) checkinDisplay.textContent = formatDisplayDate(formatDate(today));
    if (checkoutDisplay) checkoutDisplay.textContent = formatDisplayDate(formatDate(tomorrow));
    
    if (checkinInput) {
        checkinInput.addEventListener('change', function() {
            const checkin = new Date(this.value);
            const nextDay = new Date(checkin);
            nextDay.setDate(nextDay.getDate() + 1);
            
            if (checkoutInput) {
                checkoutInput.min = formatDate(nextDay);
                checkoutInput.value = formatDate(nextDay);
            }
            
            if (checkinDisplay) checkinDisplay.textContent = formatDisplayDate(this.value);
            if (checkoutDisplay) checkoutDisplay.textContent = formatDisplayDate(formatDate(nextDay));
        });
    }
    
    if (checkoutInput) {
        checkoutInput.addEventListener('change', function() {
            if (checkoutDisplay) checkoutDisplay.textContent = formatDisplayDate(this.value);
        });
    }
    
    const guestsSelect = document.getElementById('guests');
    const finalGuests = document.getElementById('final-guests');
    
    if (guestsSelect && finalGuests) {
        guestsSelect.addEventListener('change', function() {
            finalGuests.textContent = this.value;
        });
    }
}

function initBookingPage() {
    setupRoomSelection();
    updateBookingSummary();
    initializeDates();
    
    selectPaymentMethod('qris'); 

    const urlParams = new URLSearchParams(window.location.search);
    const roomParam = urlParams.get('room');
    if (roomParam && roomData[roomParam]) {
        selectedRoom = roomParam;
        
        const roomOption = document.querySelector(`.room-option[data-room="${roomParam}"]`);
        if (roomOption) {
            document.querySelectorAll('.room-option').forEach(opt => opt.classList.remove('selected'));
            roomOption.classList.add('selected');
            updateBookingSummary();
        }
    }
    
    const bookingPopup = document.getElementById('bookingPopup');
    if (bookingPopup) {
        bookingPopup.addEventListener('click', function(e) {
            if (e.target === this) {
                closePopup();
            }
        });
    }
    
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closePopup();
        }
    });
}

document.addEventListener('DOMContentLoaded', function() {
    initBookingPage();
});
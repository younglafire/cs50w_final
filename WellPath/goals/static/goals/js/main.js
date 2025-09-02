// WellPath - Modern JavaScript Framework

class WellPathUI {
  constructor() {
    this.init();
  }

  init() {
    this.setupFormValidation();
    this.setupButtonLoading();
    this.setupTooltips();
    this.setupAnimations();
  }

  // Form Validation Enhancement
  setupFormValidation() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
      const inputs = form.querySelectorAll('input[required]');
      
      inputs.forEach(input => {
        input.addEventListener('blur', () => this.validateField(input));
        input.addEventListener('input', () => this.clearFieldError(input));
      });

      form.addEventListener('submit', (e) => {
        if (!this.validateForm(form)) {
          e.preventDefault();
        } else {
          this.showButtonLoading(form.querySelector('button[type="submit"]'));
        }
      });
    });
  }

  validateField(field) {
    const value = field.value.trim();
    const fieldGroup = field.closest('.form-group');
    
    // Remove existing error states
    this.clearFieldError(field);
    
    if (!value && field.hasAttribute('required')) {
      this.showFieldError(field, 'This field is required');
      return false;
    }

    // Email validation
    if (field.type === 'email' && value) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(value)) {
        this.showFieldError(field, 'Please enter a valid email address');
        return false;
      }
    }

    // Password validation
    if (field.type === 'password' && field.name === 'password1' && value) {
      if (value.length < 8) {
        this.showFieldError(field, 'Password must be at least 8 characters long');
        return false;
      }
    }

    // Password confirmation
    if (field.name === 'password2' && value) {
      const password1 = document.querySelector('input[name="password1"]');
      if (password1 && value !== password1.value) {
        this.showFieldError(field, 'Passwords do not match');
        return false;
      }
    }

    return true;
  }

  showFieldError(field, message) {
    field.classList.add('is-invalid');
    
    let errorDiv = field.parentNode.querySelector('.invalid-feedback');
    if (!errorDiv) {
      errorDiv = document.createElement('div');
      errorDiv.className = 'invalid-feedback';
      field.parentNode.appendChild(errorDiv);
    }
    errorDiv.textContent = message;
  }

  clearFieldError(field) {
    field.classList.remove('is-invalid');
    const errorDiv = field.parentNode.querySelector('.invalid-feedback');
    if (errorDiv) {
      errorDiv.remove();
    }
  }

  validateForm(form) {
    const inputs = form.querySelectorAll('input[required]');
    let isValid = true;

    inputs.forEach(input => {
      if (!this.validateField(input)) {
        isValid = false;
      }
    });

    return isValid;
  }

  // Button Loading States
  setupButtonLoading() {
    const buttons = document.querySelectorAll('button[type="submit"]');
    
    buttons.forEach(button => {
      button.addEventListener('click', () => {
        setTimeout(() => this.showButtonLoading(button), 100);
      });
    });
  }

  showButtonLoading(button) {
    if (!button) return;
    
    button.classList.add('btn-loading');
    button.disabled = true;
    
    // Reset after 3 seconds (fallback)
    setTimeout(() => {
      this.hideButtonLoading(button);
    }, 3000);
  }

  hideButtonLoading(button) {
    if (!button) return;
    
    button.classList.remove('btn-loading');
    button.disabled = false;
  }

  // Tooltip Setup
  setupTooltips() {
    // Initialize Bootstrap tooltips if available
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
      const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
      tooltipTriggerList.map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
    }
  }

  // Smooth Animations
  setupAnimations() {
    // Fade in animation for cards
    const cards = document.querySelectorAll('.card-modern');
    
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.style.opacity = '1';
          entry.target.style.transform = 'translateY(0)';
        }
      });
    }, { threshold: 0.1 });

    cards.forEach((card, index) => {
      card.style.opacity = '0';
      card.style.transform = 'translateY(20px)';
      card.style.transition = `opacity 0.6s ease ${index * 0.1}s, transform 0.6s ease ${index * 0.1}s`;
      observer.observe(card);
    });
  }

  // Alert Auto-dismiss
  setupAlerts() {
    const alerts = document.querySelectorAll('.alert-modern');
    
    alerts.forEach(alert => {
      // Auto-dismiss after 5 seconds
      setTimeout(() => {
        alert.style.opacity = '0';
        alert.style.transform = 'translateX(100%)';
        setTimeout(() => alert.remove(), 300);
      }, 5000);

      // Manual dismiss
      const closeBtn = alert.querySelector('.btn-close');
      if (closeBtn) {
        closeBtn.addEventListener('click', () => {
          alert.style.opacity = '0';
          alert.style.transform = 'translateX(100%)';
          setTimeout(() => alert.remove(), 300);
        });
      }
    });
  }

  // Utility Methods
  showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type}-modern alert-modern`;
    notification.innerHTML = `
      ${message}
      <button type="button" class="btn-close" aria-label="Close"></button>
    `;
    
    document.body.appendChild(notification);
    this.setupAlerts();
  }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  new WellPathUI();
});

// Export for use in other scripts
window.WellPathUI = WellPathUI;
// =====================================================
// TeaVision — interactivity
// =====================================================

// Footer year
document.getElementById('year').textContent = new Date().getFullYear();

// Sticky navbar shadow on scroll
const navbar = document.getElementById('navbar');
const onScroll = () => navbar.classList.toggle('scrolled', window.scrollY > 24);
window.addEventListener('scroll', onScroll, { passive: true });
onScroll();

// Mobile menu toggle
const navToggle = document.getElementById('navToggle');
const navLinks = document.getElementById('navLinks');
navToggle.addEventListener('click', () => navLinks.classList.toggle('open'));
navLinks.addEventListener('click', e => {
  if (e.target.tagName === 'A') navLinks.classList.remove('open');
});

// Reveal-on-scroll for cards / sections
const revealTargets = document.querySelectorAll(
  '.card, .obj, .sol-card, .sol-extra, .tech, .tl-item, .metric, .doc, .member, .counter, .stat, .pillar'
);
revealTargets.forEach(el => el.classList.add('reveal'));

const io = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
      io.unobserve(entry.target);
    }
  });
}, { threshold: 0.12 });

revealTargets.forEach(el => io.observe(el));

// Animated counters
const counters = document.querySelectorAll('.counter h3, .stat h3');
const animateCounter = (el) => {
  const text = el.textContent.trim();
  const match = text.match(/^(\d+)(.*)$/);
  if (!match) return;
  const target = parseInt(match[1], 10);
  const suffix = match[2];
  let current = 0;
  const step = Math.max(1, Math.ceil(target / 40));
  const tick = () => {
    current += step;
    if (current >= target) {
      el.textContent = target + suffix;
      return;
    }
    el.textContent = current + suffix;
    requestAnimationFrame(tick);
  };
  tick();
};

const counterIO = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      animateCounter(entry.target);
      counterIO.unobserve(entry.target);
    }
  });
}, { threshold: 0.6 });

counters.forEach(c => counterIO.observe(c));

// ── EmailJS Contact Form ──
(function() {
  emailjs.init({ publicKey: 'sdUb9nObomp06BX2a' });

  const contactForm = document.getElementById('contactForm');
  const contactBtn = document.getElementById('contactBtn');
  const contactStatus = document.getElementById('contactStatus');

  contactForm.addEventListener('submit', function (e) {
    e.preventDefault();
    contactBtn.disabled = true;
    contactBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Sending...';
    contactStatus.style.display = 'none';

    var templateParams = {
      from_name: contactForm.from_name.value,
      from_email: contactForm.from_email.value,
      subject: contactForm.subject.value,
      message: contactForm.message.value
    };

    emailjs.send('service_5a4rbzm', 'template_xo3ujvu', templateParams)
      .then(function () {
        contactStatus.style.display = 'block';
        contactStatus.style.color = '#4ade80';
        contactStatus.textContent = 'Message sent successfully! We will get back to you soon.';
        contactForm.reset();
        contactBtn.disabled = false;
        contactBtn.innerHTML = 'Send Message <i class="fa-solid fa-paper-plane"></i>';
      })
      .catch(function (err) {
        contactStatus.style.display = 'block';
        contactStatus.style.color = '#f87171';
        contactStatus.textContent = 'Failed to send. Please email us directly at nipunaabeysekara2001@gmail.com';
        contactBtn.disabled = false;
        contactBtn.innerHTML = 'Send Message <i class="fa-solid fa-paper-plane"></i>';
      });
  });
})();

// Animate metric bars when visible
const bars = document.querySelectorAll('.bar-fill');
bars.forEach(bar => {
  const target = bar.style.width;
  bar.style.width = '0%';
  const barIO = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        bar.style.width = target;
        barIO.unobserve(bar);
      }
    });
  }, { threshold: 0.3 });
  barIO.observe(bar);
});

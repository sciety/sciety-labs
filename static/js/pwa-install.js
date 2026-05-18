(function () {
    var deferredPrompt = null;

    if (window.matchMedia('(display-mode: standalone)').matches) {
        return;
    }

    window.addEventListener('beforeinstallprompt', function (e) {
        e.preventDefault();
        deferredPrompt = e;
        document.getElementById('pwa-install-item').hidden = false;
    });

    window.addEventListener('appinstalled', function () {
        document.getElementById('pwa-install-item').hidden = true;
        deferredPrompt = null;
    });

    document.addEventListener('DOMContentLoaded', function () {
        document.getElementById('pwa-install-btn').addEventListener('click', function () {
            if (!deferredPrompt) return;
            deferredPrompt.prompt();
            deferredPrompt.userChoice.then(function () {
                deferredPrompt = null;
                document.getElementById('pwa-install-item').hidden = true;
            });
        });
    });
})();

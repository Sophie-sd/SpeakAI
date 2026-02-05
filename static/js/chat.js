/**
 * Chat Logic - Senior Implementation
 * Handles automatic scrolling and message lifecycle.
 */

(function() {
    const chatConfig = {
        historyId: 'chat-history',
        scrollThreshold: 150 // pixels from bottom to trigger auto-scroll
    };

    /**
     * Scroll the chat history to the bottom.
     * @param {boolean} smooth - Whether to use smooth scrolling.
     */
    function scrollToBottom(smooth = true) {
        const history = document.getElementById(chatConfig.historyId);
        if (!history) return;

        history.scrollTo({
            top: history.scrollHeight,
            behavior: smooth ? 'smooth' : 'auto'
        });
    }

    /**
     * Check if the chat is already at the bottom.
     * @returns {boolean}
     */
    function isAtBottom() {
        const history = document.getElementById(chatConfig.historyId);
        if (!history) return false;
        
        const offset = history.scrollHeight - history.scrollTop - history.clientHeight;
        return offset < chatConfig.scrollThreshold;
    }

    // Initialize scrolling on load
    document.addEventListener('DOMContentLoaded', () => {
        scrollToBottom(false);
    });

    // Handle HTMX events for new messages
    document.addEventListener('htmx:afterSettle', (event) => {
        // If the update was to the chat history, scroll down
        if (event.detail.target.id === chatConfig.historyId) {
            scrollToBottom(true);
        }
    });

    // Export to global scope if needed
    window.chatUtils = {
        scrollToBottom,
        isAtBottom
    };

    /**
     * Event delegation for translation toggle buttons.
     */
    document.addEventListener('click', (e) => {
        const btn = e.target.closest('.btn-translation[data-translation-target]');
        if (!btn) return;

        const messageId = btn.dataset.translationTarget;
        const block = document.getElementById(`translation-${messageId}`);
        const textSpan = btn.querySelector('.text');
        if (!block || !textSpan) return;

        if (block.classList.contains('translation-block-hidden')) {
            block.classList.remove('translation-block-hidden');
            textSpan.textContent = 'Приховати переклад';
        } else {
            block.classList.add('translation-block-hidden');
            textSpan.textContent = 'Переглянути переклад';
        }
    });
})();

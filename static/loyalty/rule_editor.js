// Loyalty Rule Visual Editor with Drag-and-Drop (using SortableJS)
// Assumes SortableJS is loaded via CDN or static (https://sortablejs.github.io/Sortable/)
// This script expects a container with id 'rule-list' and rule cards with class 'rule-card'.

// Initialize drag-and-drop for rule list
function initRuleDragAndDrop() {
    const ruleList = document.getElementById('rule-list');
    if (!ruleList || typeof Sortable === 'undefined') return;
    Sortable.create(ruleList, {
        animation: 150,
        handle: '.drag-handle',
        ghostClass: 'drag-ghost',
        onEnd: function (evt) {
            // Optionally update order in a hidden input or via AJAX
            updateRuleOrder();
        }
    });
}

// Update the order of rules in a hidden input for form submission
function updateRuleOrder() {
    const ruleList = document.getElementById('rule-list');
    const orderInput = document.getElementById('rule-order-input');
    if (!ruleList || !orderInput) return;
    const ids = Array.from(ruleList.children).map(card => card.dataset.ruleId);
    orderInput.value = ids.join(',');
}

// Call this after DOM is ready
if (document.readyState !== 'loading') {
    initRuleDragAndDrop();
} else {
    document.addEventListener('DOMContentLoaded', initRuleDragAndDrop);
}

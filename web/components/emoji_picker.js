/**
 * A simple emoji picker component.
 * Creates a panel of common emojis that can be selected.
 */

const COMMON_EMOJIS = [
    '📁', '📊', '📈', '📝', '📌', '🔖', '📚', '🗂️', '📂', '📄',
    '✅', '⏰', '🔔', '🏆', '🎯', '💡', '🔍', '🔑', '🚀', '⭐',
    '🏠', '🏢', '🌟', '🔧', '🛠️', '📱', '💻', '📅', '🗓️', '📆',
    '📎', '🔗', '📤', '📥', '📨', '📩', '🎁', '🎨', '🎬', '🎮' 
];

export function createEmojiPicker(inputElement, buttonElement) {
    // Create the picker container
    const picker = document.createElement('div');
    picker.className = 'emoji-picker';
    picker.style.display = 'none';
    picker.style.position = 'absolute';
    picker.style.zIndex = '9999';
    picker.style.background = '#fff';
    picker.style.border = '1px solid #ddd';
    picker.style.borderRadius = '4px';
    picker.style.padding = '8px';
    picker.style.boxShadow = '0 2px 10px rgba(0, 0, 0, 0.1)';
    picker.style.width = '240px';
    picker.style.flexWrap = 'wrap';
    picker.style.display = 'none';
    picker.style.gridTemplateColumns = 'repeat(8, 1fr)';
    picker.style.maxHeight = '240px'; // Limit height
    picker.style.overflowY = 'auto'; // Allow scrolling if needed
    
    // Dark mode styling for better contrast
    picker.style.background = '#2a2a2a';
    picker.style.color = '#fff';
    picker.style.border = '1px solid #555';
    
    // Add emojis to the picker
    COMMON_EMOJIS.forEach(emoji => {
        const emojiElement = document.createElement('div');
        emojiElement.className = 'emoji-item';
        emojiElement.textContent = emoji;
        emojiElement.style.cursor = 'pointer';
        emojiElement.style.padding = '5px';
        emojiElement.style.fontSize = '20px';
        emojiElement.style.textAlign = 'center';
        emojiElement.style.borderRadius = '4px';
        emojiElement.style.transition = 'background 0.2s';
        
        emojiElement.addEventListener('mouseover', () => {
            emojiElement.style.background = '#555';
        });
        
        emojiElement.addEventListener('mouseout', () => {
            emojiElement.style.background = 'transparent';
        });
        
        emojiElement.addEventListener('click', () => {
            inputElement.value = emoji;
            togglePicker();
        });
        
        picker.appendChild(emojiElement);
    });
    
    // Position the picker near the button
    function positionPicker() {
        const buttonRect = buttonElement.getBoundingClientRect();
        const pickerHeight = 240; // Approximate height
        
        // Check if there's enough space above the button
        const spaceAbove = buttonRect.top;
        const spaceBelow = window.innerHeight - buttonRect.bottom;
        
        if (spaceAbove > pickerHeight || spaceAbove > spaceBelow) {
            // Position above if there's enough space or more than below
            picker.style.top = (buttonRect.top + window.scrollY - pickerHeight - 5) + 'px';
            picker.style.left = (buttonRect.left + window.scrollX) + 'px';
        } else {
            // Position below if there's more space below
            picker.style.top = (buttonRect.bottom + window.scrollY + 5) + 'px';
            picker.style.left = (buttonRect.left + window.scrollX) + 'px';
        }
    }
    
    // Toggle picker visibility
    function togglePicker() {
        if (picker.style.display === 'none' || picker.style.display === '') {
            positionPicker();
            picker.style.display = 'grid';
            
            // Add a click listener to close the picker when clicking outside
            document.addEventListener('click', clickOutside);
        } else {
            picker.style.display = 'none';
            document.removeEventListener('click', clickOutside);
        }
    }
    
    // Close picker when clicking outside
    function clickOutside(event) {
        if (!picker.contains(event.target) && event.target !== buttonElement) {
            picker.style.display = 'none';
            document.removeEventListener('click', clickOutside);
        }
    }
    
    // Close on ESC key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && picker.style.display !== 'none') {
            picker.style.display = 'none';
            document.removeEventListener('click', clickOutside);
        }
    });
    
    // Toggle picker when button is clicked
    buttonElement.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        togglePicker();
    });
    
    // Add the picker to the document
    document.body.appendChild(picker);
    
    return {
        element: picker,
        toggle: togglePicker,
        close: () => {
            picker.style.display = 'none';
            document.removeEventListener('click', clickOutside);
        }
    };
} 
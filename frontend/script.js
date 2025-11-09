// Basic setup for API access and app state.
// Use the current origin so it works both locally and in deployment.
const API_BASE = window.location.origin;
let authToken = null;        // Stores the JWT token
let currentUser = null;      // Holds the signed-in user
let resources = [];          // Cache of tradable items
let portfolioChart = null;  // Chart.js instance for the holdings chart
let currentPositions = [];  // Current holdings

// Restore any saved session when the page loads.
document.addEventListener('DOMContentLoaded', function() {
    // Try to restore session from localStorage
    authToken = localStorage.getItem('authToken');
    currentUser = JSON.parse(localStorage.getItem('currentUser') || 'null');
    
    if (authToken && currentUser) {
        // User is already logged in - show the main app
        showMainApp();
        loadMainAppData();
        startAutomaticUpdates(); // Start automatic price updates
    } else {
        // No saved session - show login/register screen
        showAuthSection();
    }
});

// Log the user in with a username and password.
async function login() {
    // Get form values
    const username = document.getElementById('loginUsername').value;
    const password = document.getElementById('loginPassword').value;
    
    // Validate input
    if (!username || !password) {
        showMessage('loginMessage', 'Please fill in all fields', 'error');
        return;
    }
    
    try {
        // Send login request to backend
        // FastAPI OAuth2 requires form-urlencoded format
        const response = await fetch(`${API_BASE}/api/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`
        });
        
        const data = await response.json();
        if (response.ok) {
            // Login successful - save token and get user info
            authToken = data.access_token;
            localStorage.setItem('authToken', authToken);
            await getCurrentUser();  // Fetch user details
            showMessage('loginMessage', 'Login successful!', 'success');
            
            // Show main app after a short delay
            setTimeout(() => {
                showMainApp();
                startAutomaticUpdates(); // Start automatic price updates
            }, 1000);
        } else {
            // Login failed - show error
            showMessage('loginMessage', data.detail || 'Login failed', 'error');
        }
    } catch (error) {
        // Network error or server not running
        showMessage('loginMessage', 'Connection error. Make sure the server is running.', 'error');
        console.error('Login error:', error);
    }
}

// Create a user account.
async function register() {
    // Get form values
    const username = document.getElementById('registerUsername').value;
    const email = document.getElementById('registerEmail').value;
    const password = document.getElementById('registerPassword').value;
    
    // Validate input
    if (!username || !email || !password) {
        showMessage('registerMessage', 'Please fill in all fields', 'error');
        return;
    }
    
    try {
        // Send registration request to backend
        const response = await fetch(`${API_BASE}/api/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email, password })
        });
        
        const data = await response.json();
        if (response.ok) {
            // Registration successful - clear form and show success message
            showMessage('registerMessage', 'Registration successful! You can now login.', 'success');
            document.getElementById('registerUsername').value = '';
            document.getElementById('registerEmail').value = '';
            document.getElementById('registerPassword').value = '';
        } else {
            // Registration failed - show error
            showMessage('registerMessage', data.detail || 'Registration failed', 'error');
        }
    } catch (error) {
        // Network error
        showMessage('registerMessage', 'Connection error. Make sure the server is running.', 'error');
        console.error('Registration error:', error);
    }
}

// Sign the user out and reset local state.
function logout() {
    // Clear authentication data
    authToken = null;
    currentUser = null;
    localStorage.removeItem('authToken');
    localStorage.removeItem('currentUser');
    
    // Show login/register screen
    showAuthSection();
}

// Show the sign-in screen.
function showAuthSection() {
    document.getElementById('authSection').classList.remove('hidden');
    document.getElementById('mainApp').classList.add('hidden');
    document.getElementById('userInfo').classList.add('hidden');
}

// Reveal the main trading screen.
function showMainApp() {
    document.getElementById('authSection').classList.add('hidden');
    document.getElementById('mainApp').classList.remove('hidden');
    document.getElementById('userInfo').classList.remove('hidden');
    loadMainAppData();  // Load all data for the main app
}

// Show a short status message to the user.
function showMessage(elementId, message, type) {
    const element = document.getElementById(elementId);
    element.innerHTML = `<div class="message ${type}">${message}</div>`;
    // Auto-hide message after 5 seconds
    setTimeout(() => { element.innerHTML = ''; }, 5000);
}

// Fetch details for the signed-in user and refresh the UI.
async function getCurrentUser() {
    try {
        // Fetch user info from backend
        const response = await fetch(`${API_BASE}/api/me`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (response.ok) {
            // Success - save user data
            currentUser = await response.json();
            localStorage.setItem('currentUser', JSON.stringify(currentUser));
        } else {
            // API call failed - use cached data
            console.error('Failed to get user info, using cached data');
        }
        // Always update the UI with current user data (cached or fresh)
        updateUserInfo();
    } catch (error) {
        // Network error - use cached data
        console.error('Error getting user info:', error);
        updateUserInfo();
    }
}

// Pull the list of resources and fall back to defaults if needed.
async function getResources() {
    try {
        const response = await fetch(`${API_BASE}/api/resources`);
        if (response.ok) {
            // Success - save resources
            resources = await response.json();
        } else {
            // API failed - use fallback data
            resources = [
                { symbol: 'ENG', name: 'Energy Units', current_price: 100.0, last_updated: new Date().toISOString() },
                { symbol: 'DTA', name: 'Digital Tokens', current_price: 50.0, last_updated: new Date().toISOString() },
                { symbol: 'CRY', name: 'Crypto Crystals', current_price: 200.0, last_updated: new Date().toISOString() },
                { symbol: 'BIO', name: 'Bio Materials', current_price: 75.0, last_updated: new Date().toISOString() },
                { symbol: 'MET', name: 'Rare Metals', current_price: 150.0, last_updated: new Date().toISOString() },
            ];
        }
        displayResources();  // Update the UI
    } catch (error) {
        // Network error - use fallback data
        console.error('Error getting resources, using defaults:', error);
        resources = [
            { symbol: 'ENG', name: 'Energy Units', current_price: 100.0, last_updated: new Date().toISOString() },
            { symbol: 'DTA', name: 'Digital Tokens', current_price: 50.0, last_updated: new Date().toISOString() },
            { symbol: 'CRY', name: 'Crypto Crystals', current_price: 200.0, last_updated: new Date().toISOString() },
            { symbol: 'BIO', name: 'Bio Materials', current_price: 75.0, last_updated: new Date().toISOString() },
            { symbol: 'MET', name: 'Rare Metals', current_price: 150.0, last_updated: new Date().toISOString() },
        ];
        displayResources();  // Update the UI with fallback data
    }
}

// Fetch positions for the current user.
async function getPositions() {
    try {
        const response = await fetch(`${API_BASE}/api/positions`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (response.ok) {
            const positions = await response.json();
            console.log('Positions data from backend:', positions); // Debug log
            currentPositions = positions; // Store globally for live updates
            displayPositions(positions);  // Update the UI
        }
    } catch (error) {
        console.error('Error getting positions:', error);
    }
}

// Fetch the trade history.
async function getTransactions() {
    try {
        console.log('Fetching transactions...');
        const response = await fetch(`${API_BASE}/api/transactions`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        console.log('Transactions response status:', response.status);
        if (response.ok) {
            const transactions = await response.json();
            console.log('Transactions data from backend:', transactions); // Debug log
            console.log('Number of transactions:', transactions.length);
            displayTransactions(transactions);
        } else {
            console.error('Failed to fetch transactions:', response.status, response.statusText);
        }
    } catch (error) {
        console.error('Error getting transactions:', error);
    }
}

async function executeTrade(resourceSymbol, quantity, tradeType) {
    try {
        const response = await fetch(`${API_BASE}/api/trade`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({ resource_symbol: resourceSymbol, quantity: parseFloat(quantity), trade_type: tradeType })
        });
        const data = await response.json();
        console.log('Trade response:', data); // Debug log
        if (response.ok) {
            alert(`${tradeType.toUpperCase()} order executed successfully!`);
            // Update the balance if the server tells us the new value.
            if (data.balance !== undefined) {
                console.log('Updating balance from trade response:', data.balance); // Debug log
                currentUser.balance = data.balance;
                localStorage.setItem('currentUser', JSON.stringify(currentUser));
                updateUserInfo();
            } else {
                console.log('No balance in trade response, fetching fresh data'); // Debug log
            }
            // Pull fresh data from the server as well.
            await getCurrentUser();
            await getPositions();
            await getTransactions();
        } else {
            alert(data.detail || 'Trade failed');
        }
    } catch (error) {
        alert('Connection error. Make sure the server is running.');
        console.error('Trade error:', error);
    }
}

function updateUserInfo() {
    if (currentUser) {
        console.log('Updating user info - Balance:', currentUser.balance);
        document.getElementById('username').textContent = currentUser.username;
        document.getElementById('userBalance').textContent = currentUser.balance.toLocaleString('en-GB', {
            style: 'currency',
            currency: 'GBP'
        }).replace('GBP', '');
    } else {
        console.log('No current user data available for update');
    }
}

function displayResources() {
    const grid = document.getElementById('resourcesGrid');
    grid.innerHTML = '';
    
    resources.forEach(resource => {
        const card = document.createElement('div');
        card.className = 'resource-card';
        card.innerHTML = `
            <div class="resource-header">
                <div class="resource-info">
                    <h3>${resource.name}</h3>
                    <div class="resource-symbol">${resource.symbol}</div>
                </div>
                <div class="resource-price">£${resource.current_price.toFixed(2)}</div>
            </div>
            <div class="trade-controls">
                <input type="number" class="quantity-input" id="qty-${resource.symbol}" placeholder="Qty" min="0.01" step="0.01" value="1">
                <button class="btn btn-success" onclick="trade('${resource.symbol}', 'buy')">BUY</button>
                <button class="btn btn-danger" onclick="trade('${resource.symbol}', 'sell')">SELL</button>
            </div>
        `;
        grid.appendChild(card);
    });
    
    // Refresh positions so the profit figures stay current.
    updatePositionsWithNewPrices();
}

function displayPositions(positions) {
    const content = document.getElementById('positionsContent');
    const table = document.getElementById('positionsTable');
    const tbody = document.getElementById('positionsTableBody');
    
    if (!positions || !positions.length) {
        content.innerHTML = '<div class="loading">No positions yet. Start trading to build your portfolio!</div>';
        table.classList.add('hidden');
        updatePortfolioChart([]);
        return;
    }
    
    content.classList.add('hidden');
    table.classList.remove('hidden');
    tbody.innerHTML = '';
    
    const chartData = [];
    
    positions.forEach(pos => {
        // Use the backend-calculated values
        const currentValue = pos.current_value || (pos.quantity * pos.resource.current_price);
        const profitLoss = pos.profit_loss || (currentValue - (pos.quantity * pos.average_price));
        const totalCost = pos.quantity * pos.average_price;
        const profitLossPercent = totalCost > 0 ? (profitLoss / totalCost) * 100 : 0;
        
        const profitLossClass = profitLoss >= 0 ? 'profit-positive' : 'profit-negative';
        const profitLossSign = profitLoss >= 0 ? '+' : '';
        
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>
                <div>
                    <strong>${pos.resource.name}</strong>
                    <div class="resource-symbol">${pos.resource.symbol}</div>
                </div>
            </td>
            <td>${pos.quantity.toFixed(2)}</td>
            <td>£${pos.average_price.toFixed(2)}</td>
            <td>£${currentValue.toFixed(2)}</td>
            <td class="${profitLossClass}">
                ${profitLossSign}£${profitLoss.toFixed(2)}
                <div style="font-size: 0.75rem; opacity: 0.8;">
                    (${profitLossSign}${profitLossPercent.toFixed(1)}%)
                </div>
            </td>
            <td><button class="btn btn-danger" onclick="sellPosition('${pos.resource.symbol}', ${pos.quantity})">Sell All</button></td>
        `;
        tbody.appendChild(row);
        
        // Add to chart data
        chartData.push({
            symbol: pos.resource.symbol,
            name: pos.resource.name,
            value: currentValue,
            color: getRandomColor()
        });
    });
    
    // Update portfolio chart
    updatePortfolioChart(chartData);
}

// Function to update positions with new prices for live P&L
function updatePositionsWithNewPrices() {
    console.log('🔄 updatePositionsWithNewPrices called');
    console.log('📊 currentPositions:', currentPositions);
    console.log('📊 currentPositions length:', currentPositions ? currentPositions.length : 'undefined');
    
    // Only update if we have positions data
    if (typeof currentPositions === 'undefined' || !currentPositions || currentPositions.length === 0) {
        console.log('⚠️ No positions data available for live P&L update');
        return;
    }
    
    const tbody = document.getElementById('positionsTableBody');
    if (!tbody) {
        console.log('❌ Positions table body not found');
        return;
    }
    
    console.log('✅ Found positions table body');
    
    console.log('Updating P&L with new prices...', { 
        positions: currentPositions.length, 
        resources: resources.length,
        currentPositions: currentPositions,
        resources: resources
    });
    
    const rows = tbody.querySelectorAll('tr');
    console.log(`📋 Found ${rows.length} table rows`);
    
    if (rows.length === 0) {
        console.log('⚠️ No position rows found - user may not have any positions');
        return;
    }
    
    rows.forEach((row, index) => {
        if (currentPositions[index]) {
            const pos = currentPositions[index];
            console.log(`Processing position ${index}:`, pos);
            
            // Find the current resource price
            const currentResource = resources.find(r => r.symbol === pos.resource.symbol);
            console.log(`Looking for resource ${pos.resource.symbol}:`, currentResource);
            
            if (currentResource) {
                const currentValue = pos.quantity * currentResource.current_price;
                const totalCost = pos.quantity * pos.average_price;
                const profitLoss = currentValue - totalCost;
                const profitLossPercent = totalCost > 0 ? (profitLoss / totalCost) * 100 : 0;
                
                const profitLossClass = profitLoss >= 0 ? 'profit-positive' : 'profit-negative';
                const profitLossSign = profitLoss >= 0 ? '+' : '';
                
                console.log(`Updating ${pos.resource.symbol}:`, {
                    quantity: pos.quantity,
                    averagePrice: pos.average_price,
                    oldPrice: pos.resource.current_price,
                    newPrice: currentResource.current_price,
                    currentValue,
                    totalCost,
                    profitLoss,
                    profitLossPercent
                });
                
                // Update the current value and P&L cells
                const cells = row.querySelectorAll('td');
                console.log(`Found ${cells.length} cells in row ${index}`);
                
                if (cells.length >= 5) {
                    cells[3].textContent = `£${currentValue.toFixed(2)}`; // Current Value
                    cells[4].innerHTML = `
                        ${profitLossSign}£${profitLoss.toFixed(2)}
                        <div style="font-size: 0.75rem; opacity: 0.8;">
                            (${profitLossSign}${profitLossPercent.toFixed(1)}%)
                        </div>
                    `;
                    cells[4].className = `profit-cell ${profitLossClass}`;
                    
                    console.log(`Updated row ${index} with P&L: ${profitLossSign}£${profitLoss.toFixed(2)}`);
                } else {
                    console.log(`Not enough cells in row ${index}: ${cells.length}`);
                }
                
                // Update the position data for chart
                pos.current_value = currentValue;
                pos.profit_loss = profitLoss;
            } else {
                console.log(`Resource not found for symbol: ${pos.resource.symbol}`);
                console.log('Available resources:', resources.map(r => r.symbol));
            }
        } else {
            console.log(`No position data for row ${index}`);
        }
    });
    
    // Update the portfolio chart with new values
    const chartData = currentPositions.map(pos => ({
        symbol: pos.resource.symbol,
        name: pos.resource.name,
        value: pos.current_value || (pos.quantity * pos.resource.current_price),
        color: getRandomColor()
    }));
    updatePortfolioChart(chartData);
}


function displayTransactions(transactions) {
    console.log('displayTransactions called with:', transactions);
    const content = document.getElementById('transactionsContent');
    const table = document.getElementById('transactionsTable');
    const tbody = document.getElementById('transactionsTableBody');
    
    if (!transactions || !transactions.length) {
        console.log('No transactions to display');
        content.innerHTML = '<div class="loading">No transactions yet.</div>';
        table.classList.add('hidden');
        return;
    }
    
    console.log('Displaying', transactions.length, 'transactions');
    
    content.classList.add('hidden');
    table.classList.remove('hidden');
    tbody.innerHTML = '';
    
    // Sort transactions by timestamp (newest first)
    const sortedTransactions = transactions.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    
    sortedTransactions.forEach(tr => {
        const typeClass = tr.transaction_type === 'buy' ? 'profit-negative' : 'profit-positive';
        const date = new Date(tr.timestamp).toLocaleString();
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>
                <div>
                    <strong>${tr.resource.name}</strong>
                    <div class="resource-symbol">${tr.resource.symbol}</div>
                </div>
            </td>
            <td class="${typeClass}">
                ${tr.transaction_type.toUpperCase()}
            </td>
            <td>${tr.quantity.toFixed(2)}</td>
            <td>£${tr.price.toFixed(2)}</td>
            <td>£${tr.total_value.toFixed(2)}</td>
            <td style="font-size: 0.75rem; color: var(--text-secondary);">${date}</td>
        `;
        tbody.appendChild(row);
    });
}

function trade(resourceSymbol, tradeType) {
    const qtyInput = document.getElementById(`qty-${resourceSymbol}`);
    const quantity = parseFloat(qtyInput.value);
    
    if (!quantity || quantity <= 0) {
        alert('Please enter a valid quantity');
        return;
    }
    
    const resource = resources.find(r => r.symbol === resourceSymbol);
    const total = quantity * resource.current_price;
    
    const confirmed = confirm(
        `${tradeType.toUpperCase()} ${quantity} ${resourceSymbol} at £${resource.current_price.toFixed(2)} each?\nTotal: £${total.toFixed(2)}`
    );
    
    if (confirmed) {
        executeTrade(resourceSymbol, quantity, tradeType);
        qtyInput.value = '1';
    }
}

function sellPosition(resourceSymbol, maxQuantity) {
    const quantity = prompt(`How many ${resourceSymbol} to sell? (Max: ${maxQuantity})`);
    if (quantity && quantity > 0 && quantity <= maxQuantity) {
        executeTrade(resourceSymbol, quantity, 'sell');
    } else if (quantity !== null) {
        alert('Invalid quantity');
    }
}

// -------------------- Main Stuff --------------------
async function loadMainAppData() {
    await getCurrentUser();
    await getResources();
    await getPositions();
    await getTransactions();
}

// Auto-refresh data every 30 seconds
async function autoRefresh() {
    if (authToken && !document.getElementById('mainApp').classList.contains('hidden')) {
        await getCurrentUser();
        await getResources();
        await getPositions();
        await getTransactions();
    }
    setTimeout(autoRefresh, 30000); // Call itself again in 30 seconds
}

// Start the auto-refresh loop on page load
setTimeout(autoRefresh, 30000);

// -------------------- Portfolio Chart Stuff --------------------
function getRandomColor() {
    const colors = [
        '#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6',
        '#06b6d4', '#84cc16', '#f97316', '#ec4899', '#6366f1'
    ];
    return colors[Math.floor(Math.random() * colors.length)];
}

function updatePortfolioChart(data) {
    const ctx = document.getElementById('portfolioChart');
    if (!ctx) return;
    
    // Destroy existing chart if it exists
    if (portfolioChart) {
        portfolioChart.destroy();
    }
    
    if (!data || data.length === 0) {
        // Show empty state
        ctx.getContext('2d').clearRect(0, 0, ctx.width, ctx.height);
        const ctx2d = ctx.getContext('2d');
        ctx2d.font = '16px Inter, sans-serif';
        ctx2d.fillStyle = '#64748b';
        ctx2d.textAlign = 'center';
        ctx2d.fillText('No portfolio data', ctx.width / 2, ctx.height / 2);
        return;
    }
    
    portfolioChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.map(item => item.symbol),
            datasets: [{
                data: data.map(item => item.value),
                backgroundColor: data.map(item => item.color),
                borderWidth: 2,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        usePointStyle: true,
                        font: {
                            family: 'Inter, sans-serif',
                            size: 12
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const item = data[context.dataIndex];
                            const total = data.reduce((sum, d) => sum + d.value, 0);
                            const percentage = ((item.value / total) * 100).toFixed(1);
                            return `${item.name}: £${item.value.toFixed(2)} (${percentage}%)`;
                        }
                    }
                }
            },
            cutout: '60%'
        }
    });
}

// Function to start automatic updates
function startAutomaticUpdates() {
    console.log('🚀 Starting automatic updates...');
    
    // Set up periodic updates for live P&L with random price changes
    setInterval(async () => {
        if (authToken && currentUser) {
            console.log('🔄 Auto-update running...');
            try {
                // First update prices with random fluctuations
                await updateResourcePrices();
                
                // Then fetch updated data
                await getResources();
                await getPositions(); // Also refresh positions data
                
                // Force update P&L with new prices
                updatePositionsWithNewPrices();
            } catch (error) {
                console.error('❌ Error in periodic update:', error);
            }
        }
    }, 2000); // Update every 2 seconds
}

// Function to update resource prices with random fluctuations
async function updateResourcePrices() {
    try {
        console.log('📈 Updating prices...');
        const response = await fetch('http://localhost:8000/api/update-prices', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            console.log('✅ Prices updated:', data.message);
        } else {
            console.error('❌ Failed to update prices:', response.statusText);
        }
    } catch (error) {
        console.error('❌ Error updating prices:', error);
    }
}

// Test function for P&L updates
async function testPandLUpdate() {
    console.log('🧪 Testing P&L update...');
    try {
        await updateResourcePrices();
        await getResources();
        await getPositions();
        updatePositionsWithNewPrices();
        console.log('✅ Test P&L update completed');
    } catch (error) {
        console.error('❌ Test P&L update failed:', error);
    }
}

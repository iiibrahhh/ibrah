let sortDirection = 'asc'; // Default sorting direction
let currentSortBy = 'price'; // Default sort column



async function fetchCryptoData(interval) {
    try {
        const response = await fetch(`/update_data?interval=${interval}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        console.log('Fetched data:', data); // إضافة هذه الرسالة لتتبع البيانات
        return data;
    } catch (error) {
        console.error('Error fetching crypto data:', error);
        return null;
    }
}

async function updateData(interval = '15m') {
    const data = await fetchCryptoData(interval);
    console.log('Data to update:', data); // إضافة هذه الرسالة لتتبع البيانات
    if (data && data.length > 0) {
        updateTable(data);
    } else {
        console.error('No data to update');
    }
}



function updateTable(data) {
    const tableBody = document.getElementById('crypto-table-body');
    tableBody.innerHTML = '';  // Clear existing data
    data.forEach(item => {
        const row = document.createElement('tr');

        const cells = [
            item.symbol || 'N/A',
            (item.price !== undefined ? item.price.toFixed(9) : 'N/A'),
            (item.RSI !== undefined ? item.RSI.toFixed(9) : 'N/A'),
            (item.MACD !== undefined ? item.MACD.toFixed(9) : 'N/A'),
            (item.SMA !== undefined ? item.SMA.toFixed(9) : 'N/A'),
            (item.EMA !== undefined ? item.EMA.toFixed(9) : 'N/A'),
            (item.ADX !== undefined ? item.ADX.toFixed(9) : 'N/A'),
            (item.CCI !== undefined ? item.CCI.toFixed(9) : 'N/A'),
            (item.OBV !== undefined ? item.OBV.toFixed(9) : 'N/A'),
            (item.BBand_mavg !== undefined ? item.BBand_mavg.toFixed(9) : 'N/A'),
            (item.BBand_hband !== undefined ? item.BBand_hband.toFixed(9) : 'N/A'),
            (item.BBand_lband !== undefined ? item.BBand_lband.toFixed(9) : 'N/A'),
            (item.ATR !== undefined ? item.ATR.toFixed(9) : 'N/A'),
            (item.FI !== undefined ? item.FI.toFixed(9) : 'N/A')
        ];

        cells.forEach(cellText => {
            const cell = document.createElement('td');
            cell.textContent = cellText;
            row.appendChild(cell);
        });

        tableBody.appendChild(row);
    });
}

document.addEventListener('DOMContentLoaded', async () => {
    const intervalSelect = document.getElementById('interval-select');
    const initialInterval = intervalSelect.value;
    await updateData(initialInterval);

    intervalSelect.addEventListener('change', async () => {
        const interval = intervalSelect.value;
        await updateData(interval);
    });

    setInterval(updateDateTime, 1000);
    setInterval(() => updateData(intervalSelect.value), 10000);
});

function updateDateTime() {
    const datetimeElement = document.getElementById('datetime');
    const now = new Date();
    datetimeElement.textContent = now.toLocaleString();
}

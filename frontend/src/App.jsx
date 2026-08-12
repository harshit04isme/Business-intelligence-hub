import React, { useState, useEffect } from 'react';
import { 
  LayoutDashboard, 
  MessageSquare, 
  Database, 
  Trash2, 
  Play, 
  Search, 
  ArrowLeft, 
  ArrowRight, 
  RefreshCw,
  Sparkles,
  DatabaseZap,
  Info
} from 'lucide-react';
import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';

// Register Chart.js structures
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [tablesMetadata, setTablesMetadata] = useState({});
  const [dbStatus, setDbStatus] = useState('loading');
  const [loadingMetadata, setLoadingMetadata] = useState(true);

  // Tab 1: Dashboard metrics
  const [kpis, setKpis] = useState({
    customers: 0,
    sales: 0,
    sessions: 0,
    tables: 0
  });
  const [clusterDistribution, setClusterDistribution] = useState([]);
  const [clusterAverages, setClusterAverages] = useState([]);

  // Tab 2: Chat states
  const [chatMessage, setChatMessage] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [chatHistory, setChatHistory] = useState([
    {
      sender: 'ai',
      text: "Hello! I am your AI Business Analyst. You can ask me natural language questions about your company database, such as:\n* *'What is the total sales amount in Groceries?'*\n* *'How many customers do we have in each region?'*\n* *'Which segment has the highest average annual income?'*",
      query: null,
      explanation: null,
      results: null
    }
  ]);

  // Tab 3: Studio states
  const [selectedTable, setSelectedTable] = useState('');
  const [gridData, setGridData] = useState([]);
  const [gridColumns, setGridColumns] = useState([]);
  const [pageSize, setPageSize] = useState(15);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalRows, setTotalRows] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchColumn, setSearchColumn] = useState('');
  const [loadingGrid, setLoadingGrid] = useState(false);
  const [editingCell, setEditingCell] = useState({ rowIndex: null, colName: null, val: '' });

  // Sandbox states
  const [sandboxSQL, setSandboxSQL] = useState('');
  const [sandboxOutput, setSandboxOutput] = useState(null);
  const [runningSandbox, setRunningSandbox] = useState(false);

  // Batch states
  const [batchAction, setBatchAction] = useState('drop_duplicates');
  const [batchColumn, setBatchColumn] = useState('');
  const [batchParamValue, setBatchParamValue] = useState('');
  const [executingBatch, setExecutingBatch] = useState(false);

  // Load database metadata
  const fetchMetadata = async (isRefresh = false) => {
    try {
      setLoadingMetadata(true);
      const res = await fetch('/api/tables');
      if (!res.ok) throw new Error("Connection failed");
      const data = await res.json();
      setTablesMetadata(data);
      setDbStatus('active');
      
      const names = Object.keys(data);
      if (names.length > 0 && !selectedTable) {
        setSelectedTable(names.includes('customer_segments') ? 'customer_segments' : names[0]);
      }
      
      // Calculate dashboard KPIs from metadata
      const tablesCount = names.length;
      const customersCount = data['customers']?.rows || 0;
      const sessionsCount = data['web_logs']?.rows || 0;
      
      setKpis(prev => ({
        ...prev,
        tables: tablesCount,
        customers: customersCount,
        sessions: sessionsCount
      }));

      // Fetch dynamic metrics for dashboards
      fetchDashboardDetails();
    } catch (e) {
      setDbStatus('error');
      console.error(e);
    } finally {
      setLoadingMetadata(false);
    }
  };

  const fetchDashboardDetails = async () => {
    try {
      // 1. Calculate sales KPI
      const salesRes = await fetch('/api/sql/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: "SELECT SUM(amount) as sales FROM transactions;" })
      });
      const salesData = await salesRes.json();
      if (salesData.type === 'select' && salesData.data.length > 0) {
        setKpis(prev => ({ ...prev, sales: salesData.data[0].sales || 0 }));
      }

      // 2. Fetch customer segments details if table exists
      const segmentCheckRes = await fetch('/api/tables');
      const meta = await segmentCheckRes.json();
      if (meta['customer_segments']) {
        const segRes = await fetch('/api/sql/execute', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            query: "SELECT cluster_id, COUNT(*) as count, AVG(age) as age, AVG(income) as income, AVG(monetary) as spend FROM customer_segments GROUP BY cluster_id ORDER BY cluster_id;"
          })
        });
        const segData = await segRes.json();
        if (segData.type === 'select') {
          setClusterDistribution(segData.data);
        }
      }
    } catch (err) {
      console.error("Dashboard metric fetch failed", err);
    }
  };

  useEffect(() => {
    fetchMetadata();
  }, []);

  // Fetch Studio Grid Data
  const fetchGridData = async () => {
    if (!selectedTable) return;
    try {
      setLoadingGrid(true);
      const url = `/api/table/${selectedTable}?page=${currentPage}&limit=${pageSize}&search=${encodeURIComponent(searchQuery)}&search_col=${searchColumn}`;
      const res = await fetch(url);
      const data = await res.json();
      
      setGridData(data.data || []);
      setTotalRows(data.total || 0);

      // Get columns list from grid data or tables metadata
      if (tablesMetadata[selectedTable]) {
        setGridColumns(tablesMetadata[selectedTable].columns);
        if (!searchColumn && tablesMetadata[selectedTable].columns.length > 0) {
          setSearchColumn(tablesMetadata[selectedTable].columns[0].name);
          setBatchColumn(tablesMetadata[selectedTable].columns[0].name);
        }
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingGrid(false);
    }
  };

  useEffect(() => {
    fetchGridData();
  }, [selectedTable, currentPage, pageSize]);

  // Trigger search on grid
  const handleSearch = (e) => {
    e.preventDefault();
    setCurrentPage(1);
    fetchGridData();
  };

  // Perform cell inline edit updates
  const handleCellClick = (rowIndex, colName, currentValue) => {
    // Determine primary key column
    const pkCol = gridColumns.find(c => c.pk)?.name || gridColumns[0]?.name;
    // Don't allow editing primary key to avoid index breakdown
    if (colName === pkCol) return;
    
    setEditingCell({ rowIndex, colName, val: currentValue });
  };

  const handleCellSave = async (e, rowIndex, colName) => {
    const pkCol = gridColumns.find(c => c.pk)?.name || gridColumns[0]?.name;
    const pkVal = gridData[rowIndex][pkCol];
    const newValue = e.target.value;

    // Quit if no changes
    if (newValue === editingCell.val) {
      setEditingCell({ rowIndex: null, colName: null, val: '' });
      return;
    }

    try {
      const res = await fetch('/api/cell/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          table: selectedTable,
          column: colName,
          value: newValue,
          pk_column: pkCol,
          pk_value: pkVal
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Update failed");
      
      // Update local state grid copy
      const updated = [...gridData];
      updated[rowIndex][colName] = newValue;
      setGridData(updated);
      
      // Refresh meta counters if affected
      fetchDashboardDetails();
    } catch (err) {
      alert(`Update Error: ${err.message}`);
    } finally {
      setEditingCell({ rowIndex: null, colName: null, val: '' });
    }
  };

  // Delete row
  const handleDeleteRow = async (pkVal) => {
    const pkCol = gridColumns.find(c => c.pk)?.name || gridColumns[0]?.name;
    if (!confirm(`Are you sure you want to delete row where ${pkCol} = ${pkVal}?`)) return;

    try {
      const res = await fetch('/api/row/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          table: selectedTable,
          pk_column: pkCol,
          pk_value: pkVal
        })
      });
      
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Deletion failed");
      }
      
      // Reload grids
      fetchGridData();
      fetchMetadata();
    } catch (err) {
      alert(`Delete Error: ${err.message}`);
    }
  };

  // Submit AI Chat Question
  const handleChatSubmit = async (e) => {
    e.preventDefault();
    if (!chatMessage.trim()) return;

    const userMessage = chatMessage;
    setChatMessage('');
    setChatLoading(true);

    // Add user message to history
    setChatHistory(prev => [...prev, { sender: 'user', text: userMessage }]);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMessage })
      });
      
      const data = await res.json();
      setChatHistory(prev => [...prev, {
        sender: 'ai',
        text: data.answer,
        query: data.sql,
        explanation: data.explanation,
        results: data.results
      }]);
    } catch (err) {
      setChatHistory(prev => [...prev, {
        sender: 'ai',
        text: "Error calling AI. Check backend server logs or API key setup.",
        query: null,
        explanation: null,
        results: null
      }]);
    } finally {
      setChatLoading(false);
      // Scroll chat window to bottom
      setTimeout(() => {
        const historyElem = document.getElementById('chat-history-win');
        if (historyElem) historyElem.scrollTop = historyElem.scrollHeight;
      }, 50);
    }
  };

  // Run custom SQL sandbox
  const handleExecuteSandbox = async () => {
    if (!sandboxSQL.trim()) return;
    setRunningSandbox(true);
    setSandboxOutput(null);

    try {
      const res = await fetch('/api/sql/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: sandboxSQL })
      });
      const data = await res.json();
      setSandboxOutput(data);
      
      // Refresh local page data
      fetchGridData();
      fetchMetadata();
    } catch (e) {
      setSandboxOutput({ type: 'error', message: 'Connection failure: ' + e.message });
    } finally {
      setRunningSandbox(false);
    }
  };

  // Batch cleaning action
  const handleExecuteBatchClean = async () => {
    if (!selectedTable) return;
    setExecutingBatch(true);
    try {
      const res = await fetch('/api/clean/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          table: selectedTable,
          action: batchAction,
          column: batchColumn,
          value: batchParamValue
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Batch execution failed.");
      alert(`Success: ${data.message}`);
      fetchGridData();
      fetchMetadata();
    } catch (err) {
      alert(`Batch Clean Error: ${err.message}`);
    } finally {
      setExecutingBatch(false);
    }
  };

  return (
    <div className="app-container">
      {/* Sidebar Navigation */}
      <nav className="sidebar">
        <div className="brand-section">
          <div className="brand-icon">⚡</div>
          <div className="brand-name">Applied AI Analyst</div>
        </div>

        <ul className="nav-links">
          <li>
            <button 
              className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`}
              onClick={() => setActiveTab('dashboard')}
            >
              <LayoutDashboard size={18} />
              Dashboard Metrics
            </button>
          </li>
          <li>
            <button 
              className={`nav-item ${activeTab === 'chat' ? 'active' : ''}`}
              onClick={() => setActiveTab('chat')}
            >
              <MessageSquare size={18} />
              AI Q&A Analyst
            </button>
          </li>
          <li>
            <button 
              className={`nav-item ${activeTab === 'studio' ? 'active' : ''}`}
              onClick={() => setActiveTab('studio')}
            >
              <Database size={18} />
              Data Studio Cleaner
            </button>
          </li>
        </ul>

        <div className="sidebar-footer">
          <div className="db-status">
            <div className={`status-dot ${dbStatus === 'active' ? '' : 'error'}`} style={{
              background: dbStatus === 'active' ? '#10b981' : (dbStatus === 'loading' ? '#eab308' : '#ef4444')
            }}></div>
            <span>
              {dbStatus === 'active' ? 'Connected (analytics.db)' : (dbStatus === 'loading' ? 'Checking DSN...' : 'Disconnect Error')}
            </span>
            <button className="action-icon-btn" onClick={() => fetchMetadata(true)} title="Refresh Schema">
              <RefreshCw size={14} style={{ marginLeft: 'auto' }} />
            </button>
          </div>
        </div>
      </nav>

      {/* Main Pages Content */}
      <main className="main-content">
        
        {/* VIEW 1: DASHBOARD METRICS */}
        {activeTab === 'dashboard' && (
          <div>
            <div className="page-header">
              <h1 className="page-title">Executive BI Dashboard</h1>
              <p className="page-subtitle">Real-time metrics, key performance indicators, and cluster distribution aggregates derived from SQLite relational schemas.</p>
            </div>

            {/* KPI Cards */}
            <div className="kpi-grid">
              <div className="glass-card kpi-card">
                <div className="kpi-icon"><Database size={24} /></div>
                <div className="kpi-info">
                  <h3>Catalog Tables</h3>
                  <div className="kpi-value">{kpis.tables}</div>
                </div>
              </div>
              <div className="glass-card kpi-card">
                <div className="kpi-icon"><MessageSquare size={24} /></div>
                <div className="kpi-info">
                  <h3>Total Customers</h3>
                  <div className="kpi-value">{kpis.customers}</div>
                </div>
              </div>
              <div className="glass-card kpi-card">
                <div className="kpi-icon"><DatabaseZap size={24} /></div>
                <div className="kpi-info">
                  <h3>Aggregate Revenue</h3>
                  <div className="kpi-value">${kpis.sales.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
                </div>
              </div>
              <div className="glass-card kpi-card">
                <div className="kpi-icon"><RefreshCw size={24} /></div>
                <div className="kpi-info">
                  <h3>Digital Footprint (Logs)</h3>
                  <div className="kpi-value">{kpis.sessions}</div>
                </div>
              </div>
            </div>

            {/* Charts View */}
            {clusterDistribution.length > 0 ? (
              <div className="charts-grid">
                <div className="glass-card">
                  <h3 className="chart-header">Customer Segment Distribution Count</h3>
                  <div style={{ height: '300px', position: 'relative' }}>
                    <Bar
                      data={{
                        labels: clusterDistribution.map(c => `Segment ${c.cluster_id}`),
                        datasets: [{
                          label: 'Number of Customers',
                          data: clusterDistribution.map(c => c.count),
                          backgroundColor: ['rgba(139, 92, 246, 0.65)', 'rgba(6, 182, 212, 0.65)', 'rgba(59, 130, 246, 0.65)', 'rgba(16, 185, 129, 0.65)'],
                          borderColor: ['#8b5cf6', '#06b6d4', '#3b82f6', '#10b981'],
                          borderWidth: 1
                        }]
                      }}
                      options={{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false } },
                        scales: {
                          y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#9ca3af' } },
                          x: { grid: { display: false }, ticks: { color: '#9ca3af' } }
                        }
                      }}
                    />
                  </div>
                </div>

                <div className="glass-card">
                  <h3 className="chart-header">Average Customer Segment Spend ($)</h3>
                  <div style={{ height: '300px', position: 'relative' }}>
                    <Bar
                      data={{
                        labels: clusterDistribution.map(c => `Segment ${c.cluster_id}`),
                        datasets: [{
                          label: 'Average monetary spend ($)',
                          data: clusterDistribution.map(c => c.spend),
                          backgroundColor: 'rgba(6, 182, 212, 0.65)',
                          borderColor: '#06b6d4',
                          borderWidth: 1
                        }]
                      }}
                      options={{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false } },
                        scales: {
                          y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#9ca3af' } },
                          x: { grid: { display: false }, ticks: { color: '#9ca3af' } }
                        }
                      }}
                    />
                  </div>
                </div>
              </div>
            ) : (
              <div className="glass-card" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                <Info size={32} style={{ marginBottom: '1rem', opacity: 0.5 }} />
                <h3>No Customer Segments Loaded</h3>
                <p style={{ marginTop: '0.5rem', fontSize: '0.9rem' }}>
                  Please ensure `customer_segments` exists in the database. Run your machine learning clustering script to instantiate segment profiling.
                </p>
              </div>
            )}
            
            {/* Table Details */}
            <div className="glass-card" style={{ marginTop: '2rem' }}>
              <h3 className="chart-header">Database Schema Catalog Summary</h3>
              <div className="grid-container" style={{ border: 'none', background: 'transparent' }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Table Name</th>
                      <th>Primary Key</th>
                      <th>Row Entries Count</th>
                      <th>Total Column Features</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.values(tablesMetadata).map(meta => (
                      <tr key={meta.name}>
                        <td style={{ fontWeight: 600 }}>{meta.name}</td>
                        <td>{meta.columns.find(c => c.pk)?.name || '-- none --'}</td>
                        <td>{meta.rows.toLocaleString()}</td>
                        <td>{meta.columns.length} columns</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* VIEW 2: AI CO-PILOT CHAT INTERFACE */}
        {activeTab === 'chat' && (
          <div className="chat-container">
            <div className="page-header">
              <h1 className="page-title">Natural Language BI Copilot</h1>
              <p className="page-subtitle">Ask direct questions. The AI translates your query to secure SQL, runs it against SQLite, and presents the results.</p>
            </div>

            <div className="chat-history" id="chat-history-win">
              {chatHistory.map((chat, idx) => (
                <div key={idx} className={`chat-bubble ${chat.sender}`}>
                  <div>{chat.text}</div>
                  
                  {/* SQL code rendering block */}
                  {chat.query && (
                    <details style={{ marginTop: '0.75rem' }}>
                      <summary style={{ cursor: 'pointer', fontSize: '0.8rem', color: '#a78bfa', fontWeight: 600 }}>
                        Inspect Executed SQL Query
                      </summary>
                      <div className="sql-block" style={{ marginTop: '0.5rem' }}>
                        <div className="sql-label">Translated SQL query</div>
                        {chat.query}
                      </div>
                    </details>
                  )}

                  {/* Tabular Output */}
                  {chat.results && chat.results.length > 0 && (
                    <details open style={{ marginTop: '0.75rem' }}>
                      <summary style={{ cursor: 'pointer', fontSize: '0.8rem', color: '#06b6d4', fontWeight: 600 }}>
                        Inspect Query Result Data ({chat.results.length} rows)
                      </summary>
                      <div className="grid-container" style={{ marginTop: '0.5rem', maxHeight: '200px', overflowY: 'auto' }}>
                        <table className="data-table">
                          <thead>
                            <tr>
                              {Object.keys(chat.results[0]).map(k => <th key={k}>{k}</th>)}
                            </tr>
                          </thead>
                          <tbody>
                            {chat.results.map((row, rIdx) => (
                              <tr key={rIdx}>
                                {Object.values(row).map((val, cIdx) => (
                                  <td key={cIdx}>{val !== null ? val.toString() : 'NULL'}</td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </details>
                  )}
                </div>
              ))}

              {chatLoading && (
                <div className="chat-bubble ai">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <div className="spinner"></div>
                    <span>AI is reading DB schema and executing SQL query...</span>
                  </div>
                </div>
              )}
            </div>

            <form onSubmit={handleChatSubmit} className="chat-input-area">
              <input
                type="text"
                placeholder="Ask e.g. 'Give me the average age of users in Segment 2' or 'total sales in books'"
                value={chatMessage}
                onChange={(e) => setChatMessage(e.target.value)}
                className="chat-input"
                disabled={chatLoading}
              />
              <button type="submit" className="btn btn-primary" disabled={chatLoading || !chatMessage.trim()}>
                <Sparkles size={16} />
                Ask Copilot
              </button>
            </form>
          </div>
        )}

        {/* VIEW 3: DATA STUDIO CLEANER */}
        {activeTab === 'studio' && (
          <div>
            <div className="page-header">
              <h1 className="page-title">Data Analyst Studio & Cleaner</h1>
              <p className="page-subtitle">Inspect raw tables, double click cell values to manually clean them, delete outlier rows, or perform batch operations.</p>
            </div>

            <div className="studio-layout">
              
              {/* Sidebar Cleaner Controls */}
              <div className="studio-panel">
                <div className="glass-card">
                  <h3 className="chart-header">Active Table Selector</h3>
                  <select
                    className="select-control"
                    value={selectedTable}
                    onChange={(e) => {
                      setSelectedTable(e.target.value);
                      setCurrentPage(1);
                      setSearchQuery('');
                      setSearchColumn('');
                      setEditingCell({ rowIndex: null, colName: null, val: '' });
                    }}
                  >
                    {Object.keys(tablesMetadata).map(name => (
                      <option key={name} value={name}>{name} ({tablesMetadata[name].rows} rows)</option>
                    ))}
                  </select>
                </div>

                {/* Batch Cleaning Toolkit */}
                <div className="glass-card">
                  <h3 className="chart-header">Batch Cleaning Toolkit</h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                    
                    <div className="tool-group">
                      <label className="tool-label">Cleaning Action</label>
                      <select 
                        className="select-control"
                        value={batchAction}
                        onChange={(e) => setBatchAction(e.target.value)}
                      >
                        <option value="drop_duplicates">Drop Duplicate Rows</option>
                        <option value="fill_na">Impose Missing Values (Fill Nulls)</option>
                        <option value="normalize_case">Standardize Text Case Casing</option>
                      </select>
                    </div>

                    {(batchAction === 'fill_na' || batchAction === 'normalize_case') && (
                      <div className="tool-group">
                        <label className="tool-label">Column Target</label>
                        <select 
                          className="select-control"
                          value={batchColumn}
                          onChange={(e) => setBatchColumn(e.target.value)}
                        >
                          {gridColumns.map(c => <option key={c.name} value={c.name}>{c.name}</option>)}
                        </select>
                      </div>
                    )}

                    {batchAction === 'fill_na' && (
                      <div className="tool-group">
                        <label className="tool-label">Fill Method / Value</label>
                        <input
                          type="text"
                          className="chat-input"
                          style={{ padding: '0.6rem 0.8rem', fontSize: '0.85rem' }}
                          placeholder="mean, mode, or custom value"
                          value={batchParamValue}
                          onChange={(e) => setBatchParamValue(e.target.value)}
                        />
                      </div>
                    )}

                    {batchAction === 'normalize_case' && (
                      <div className="tool-group">
                        <label className="tool-label">Text Case Target</label>
                        <select 
                          className="select-control"
                          value={batchParamValue}
                          onChange={(e) => setBatchParamValue(e.target.value)}
                        >
                          <option value="title">Title Case (e.g. Word Case)</option>
                          <option value="upper">UPPERCASE</option>
                          <option value="lower">lowercase</option>
                        </select>
                      </div>
                    )}

                    <button 
                      className="btn btn-primary" 
                      onClick={handleExecuteBatchClean}
                      disabled={executingBatch || !selectedTable}
                    >
                      {executingBatch ? 'Processing...' : 'Run Cleaning Operation'}
                    </button>

                  </div>
                </div>

                {/* SQL Sandbox */}
                <div className="glass-card sandbox-card">
                  <h3 className="chart-header">SQL Sandbox Executor</h3>
                  <textarea
                    placeholder="Write a custom SQL query: e.g. UPDATE transactions SET category = 'Groceries' WHERE category = 'groceries';"
                    className="sandbox-area"
                    value={sandboxSQL}
                    onChange={(e) => setSandboxSQL(e.target.value)}
                  />
                  <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                    <button 
                      className="btn btn-secondary" 
                      onClick={handleExecuteSandbox}
                      disabled={runningSandbox || !sandboxSQL.trim()}
                    >
                      <Play size={14} />
                      Run Command
                    </button>
                    {runningSandbox && <div className="spinner"></div>}
                  </div>

                  {sandboxOutput && (
                    <div className={`sandbox-notification ${sandboxOutput.type === 'error' ? 'error' : 'success'}`}>
                      <strong>Output: </strong> {sandboxOutput.message}

                      {sandboxOutput.type === 'select' && sandboxOutput.rowCount > 0 && (
                        <div style={{ marginTop: '0.75rem', maxHeight: '150px', overflowY: 'auto' }}>
                          <pre style={{ fontSize: '0.75rem', color: '#c7d2fe' }}>
                            {JSON.stringify(sandboxOutput.data.slice(0, 5), null, 2)}
                          </pre>
                          {sandboxOutput.rowCount > 5 && <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>+ {sandboxOutput.rowCount - 5} more rows</div>}
                        </div>
                      )}
                    </div>
                  )}
                </div>

              </div>

              {/* Data Table Grid */}
              <div className="glass-card" style={{ overflow: 'hidden' }}>
                <div className="studio-grid-header">
                  <h3 className="chart-header" style={{ marginBottom: 0 }}>
                    Table Browser: <span style={{ color: 'var(--primary)' }}>{selectedTable}</span>
                  </h3>
                  
                  {/* Search bar inside grid */}
                  <form onSubmit={handleSearch} style={{ display: 'flex', gap: '0.5rem' }}>
                    <select
                      className="select-control"
                      style={{ padding: '0.5rem', fontSize: '0.85rem', width: '120px' }}
                      value={searchColumn}
                      onChange={(e) => setSearchColumn(e.target.value)}
                    >
                      {gridColumns.map(c => <option key={c.name} value={c.name}>{c.name}</option>)}
                    </select>
                    <input
                      type="text"
                      className="chat-input"
                      style={{ padding: '0.5rem 1rem', fontSize: '0.85rem', width: '180px' }}
                      placeholder="search value..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                    />
                    <button type="submit" className="btn btn-secondary" style={{ padding: '0.5rem 1rem' }}>
                      <Search size={14} />
                    </button>
                  </form>
                </div>

                {loadingGrid ? (
                  <div style={{ height: '300px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <div className="spinner" style={{ width: '40px', height: '40px' }}></div>
                  </div>
                ) : gridData.length > 0 ? (
                  <div>
                    <div className="grid-container">
                      <table className="data-table">
                        <thead>
                          <tr>
                            <th>Action</th>
                            {gridColumns.map(col => (
                              <th key={col.name}>{col.name} {col.pk ? '🔑' : ''}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {gridData.map((row, rIdx) => {
                            const pkCol = gridColumns.find(c => c.pk)?.name || gridColumns[0]?.name;
                            const pkVal = row[pkCol];
                            
                            return (
                              <tr key={rIdx}>
                                <td>
                                  <button className="action-icon-btn" onClick={() => handleDeleteRow(pkVal)} title="Delete row">
                                    <Trash2 size={15} />
                                  </button>
                                </td>
                                {gridColumns.map(col => {
                                  const cellVal = row[col.name];
                                  const isEditing = editingCell.rowIndex === rIdx && editingCell.colName === col.name;
                                  
                                  return (
                                    <td 
                                      key={col.name} 
                                      className={col.pk ? '' : 'cell-editable'}
                                      onClick={() => !col.pk && handleCellClick(rIdx, col.name, cellVal)}
                                    >
                                      {isEditing ? (
                                        <input
                                          type="text"
                                          defaultValue={cellVal === null ? '' : cellVal}
                                          className="cell-edit-input"
                                          autoFocus
                                          onBlur={(e) => handleCellSave(e, rIdx, col.name)}
                                          onKeyDown={(e) => {
                                            if (e.key === 'Enter') handleCellSave(e, rIdx, col.name);
                                            if (e.key === 'Escape') setEditingCell({ rowIndex: null, colName: null, val: '' });
                                          }}
                                        />
                                      ) : (
                                        cellVal === null ? <em style={{ color: 'var(--text-muted)' }}>NULL</em> : cellVal.toString()
                                      )}
                                    </td>
                                  );
                                })}
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>

                    {/* Pagination Bar */}
                    <div className="pagination">
                      <span className="pagination-info">
                        Showing {(currentPage-1)*pageSize + 1} to {Math.min(currentPage*pageSize, totalRows)} of {totalRows} entries
                      </span>
                      <div className="pagination-controls">
                        <button 
                          className="btn btn-secondary" 
                          style={{ padding: '0.4rem 0.8rem' }}
                          disabled={currentPage === 1}
                          onClick={() => setCurrentPage(prev => prev - 1)}
                        >
                          <ArrowLeft size={14} /> Prev
                        </button>
                        <button 
                          className="btn btn-secondary" 
                          style={{ padding: '0.4rem 0.8rem' }}
                          disabled={currentPage * pageSize >= totalRows}
                          onClick={() => setCurrentPage(prev => prev + 1)}
                        >
                          Next <ArrowRight size={14} />
                        </button>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div style={{ height: '200px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#9ca3af' }}>
                    No records found matching search filters.
                  </div>
                )}

              </div>

            </div>
          </div>
        )}

      </main>
    </div>
  );
}

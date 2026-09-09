import fs from 'fs';
import path from 'path';
import AlertCard, { Alert } from '@/components/AlertCard';

export default async function MorningBrief() {
  let alerts: Alert[] = [];
  let errorMsg = null;
  
  try {
    const res = await fetch('http://127.0.0.1:8000/morning-brief', { cache: 'no-store' });
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data)) {
        alerts = data;
      } else if (data.error) {
        errorMsg = data.error;
      }
    } else {
      errorMsg = "Failed to fetch from backend (status " + res.status + ")";
    }
  } catch (error: any) {
    console.error("Error fetching alerts:", error);
    errorMsg = error.message;
  }

  // Fallback to mock data if backend fails
  if (alerts.length === 0 && errorMsg) {
    try {
      const dataDir = path.join(process.cwd(), 'data');
      const alertsFilePath = path.join(dataDir, 'alerts.json');
      const fileContents = fs.readFileSync(alertsFilePath, 'utf8');
      alerts = JSON.parse(fileContents);
    } catch (e) {
      console.error("Error loading fallback mock alerts:", e);
    }
  }

  return (
    <main className="min-h-screen max-w-3xl mx-auto p-4 md:p-8">
      <header className="mb-8 border-b border-slate-200 pb-4">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold text-[var(--color-navy)]">Morning Brief</h1>
          <div className="text-sm text-slate-500 bg-white px-3 py-1 rounded-full shadow-sm border border-slate-100">
            {new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })}
          </div>
        </div>
        <p className="text-slate-500 mt-2">Here are your priorities for today.</p>
      </header>

      {errorMsg && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          <strong>Backend Error:</strong> {errorMsg}
          <br/>
          <span className="text-red-500">Showing fallback mock data instead.</span>
        </div>
      )}

      <div className="space-y-2">
        {alerts.length > 0 ? (
          alerts.map((alert) => (
            <AlertCard key={alert.id} alert={alert} />
          ))
        ) : (
          <div className="text-center py-10 text-slate-500 bg-white rounded-xl border border-dashed border-slate-300">
            No alerts for today. You're all caught up!
          </div>
        )}
      </div>
    </main>
  );
}

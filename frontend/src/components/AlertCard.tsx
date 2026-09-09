import React from 'react';

export type AlertPriority = 'Urgent' | 'Attention' | 'Opportunity';

export interface Alert {
  id: string;
  priority: AlertPriority;
  type: string;
  title: string;
  detail: string;
  recommendation: string;
  action_required: string;
}

interface AlertCardProps {
  alert: Alert;
}

export default function AlertCard({ alert }: AlertCardProps) {
  // Determine styles based on priority
  let borderClass = 'border-[var(--color-navy)]';
  let badgeClass = 'bg-[var(--color-navy)] text-white';
  
  if (alert.priority === 'Urgent') {
    borderClass = 'border-[var(--color-urgent-border)]';
    badgeClass = 'bg-[var(--color-urgent-bg)] text-[var(--color-urgent-text)]';
  } else if (alert.priority === 'Attention') {
    borderClass = 'border-[var(--color-attention-border)]';
    badgeClass = 'bg-[var(--color-attention-bg)] text-[var(--color-attention-text)]';
  } else if (alert.priority === 'Opportunity') {
    borderClass = 'border-[var(--color-opportunity-border)]';
    badgeClass = 'bg-[var(--color-opportunity-bg)] text-[var(--color-opportunity-text)]';
  }

  return (
    <div className={`bg-white rounded-xl shadow-sm border-l-4 p-5 mb-4 ${borderClass} transition-shadow hover:shadow-md`}>
      <div className="flex justify-between items-start mb-2">
        <h3 className="text-lg font-bold text-[var(--color-navy)]">{alert.title}</h3>
        <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider ${badgeClass}`}>
          {alert.priority}
        </span>
      </div>
      
      <div className="mb-4 text-slate-600 text-sm">
        <p className="mb-2">{alert.detail}</p>
        <div className="bg-slate-50 p-3 rounded-md border border-slate-100">
          <p className="font-medium text-[var(--color-teal)] mb-1 flex items-center">
            <svg className="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            Recommendation
          </p>
          <p className="text-slate-700">{alert.recommendation}</p>
        </div>
      </div>
      
      <div className="flex flex-wrap gap-2 mt-4 pt-4 border-t border-slate-100">
        <button className="flex-1 min-w-[100px] bg-[var(--color-teal)] hover:bg-[var(--color-teal-light)] text-white font-medium py-2 px-4 rounded transition-colors text-sm">
          Approve
        </button>
        <button className="flex-1 min-w-[100px] bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 font-medium py-2 px-4 rounded transition-colors text-sm">
          Modify
        </button>
        <button className="flex-1 min-w-[100px] bg-white border border-red-200 hover:bg-red-50 text-red-600 font-medium py-2 px-4 rounded transition-colors text-sm">
          Reject
        </button>
      </div>
    </div>
  );
}

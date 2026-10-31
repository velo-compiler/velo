import React from 'react';
import { Info, Lightbulb, AlertTriangle, AlertCircle, ShieldAlert } from 'lucide-react';

interface CalloutProps {
  type: 'note' | 'tip' | 'important' | 'warning' | 'caution';
  title?: string;
  text: string;
}

export const Callout: React.FC<CalloutProps> = ({ type, title, text }) => {
  const configs = {
    note: {
      border: 'border-blue-500/40',
      bg: 'bg-blue-950/20',
      iconColor: 'text-blue-400',
      titleColor: 'text-blue-300',
      defaultTitle: 'Note',
      Icon: Info,
    },
    tip: {
      border: 'border-emerald-500/40',
      bg: 'bg-emerald-950/20',
      iconColor: 'text-emerald-400',
      titleColor: 'text-emerald-300',
      defaultTitle: 'Pro Tip',
      Icon: Lightbulb,
    },
    important: {
      border: 'border-cyan-500/40',
      bg: 'bg-cyan-950/20',
      iconColor: 'text-cyan-400',
      titleColor: 'text-cyan-300',
      defaultTitle: 'Important',
      Icon: AlertCircle,
    },
    warning: {
      border: 'border-amber-500/40',
      bg: 'bg-amber-950/20',
      iconColor: 'text-amber-400',
      titleColor: 'text-amber-300',
      defaultTitle: 'Warning',
      Icon: AlertTriangle,
    },
    caution: {
      border: 'border-rose-500/40',
      bg: 'bg-rose-950/20',
      iconColor: 'text-rose-400',
      titleColor: 'text-rose-300',
      defaultTitle: 'Caution',
      Icon: ShieldAlert,
    },
  };

  const config = configs[type] || configs.note;
  const IconComponent = config.Icon;

  return (
    <div className={`my-5 rounded-xl border ${config.border} ${config.bg} p-4.5 text-sm transition-all shadow-sm`}>
      <div className="flex items-start gap-3">
        <IconComponent className={`w-5 h-5 shrink-0 mt-0.5 ${config.iconColor}`} />
        <div className="space-y-1">
          <div className={`font-semibold tracking-wide text-xs uppercase font-sans ${config.titleColor}`}>
            {title || config.defaultTitle}
          </div>
          <div className="text-slate-300 leading-relaxed font-sans text-[13.5px]">
            {text}
          </div>
        </div>
      </div>
    </div>
  );
};


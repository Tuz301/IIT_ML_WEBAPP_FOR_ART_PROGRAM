// Enhanced StatCard.tsx - More Colorful
import { motion } from 'framer-motion';
import { LucideIcon, TrendingUp, TrendingDown } from 'lucide-react';
import { useEffect, useState } from 'react';

interface StatCardProps {
  icon: LucideIcon;
  label: string;
  value: number | string;
  trend: string;
  trendUp: boolean;
  color: 'blue' | 'red' | 'amber' | 'green' | 'purple' | 'cyan';
}

const colorClasses = {
  blue: {
    bg: 'bg-gradient-to-br from-blue-400 to-cyan-500',
    iconBg: 'bg-blue-100',
    iconColor: 'text-blue-600',
    trendUp: 'bg-cyan-100 text-cyan-700',
    trendDown: 'bg-blue-100 text-blue-700',
  },
  red: {
    bg: 'bg-gradient-to-br from-red-400 to-pink-500',
    iconBg: 'bg-red-100',
    iconColor: 'text-red-600',
    trendUp: 'bg-pink-100 text-pink-700',
    trendDown: 'bg-red-100 text-red-700',
  },
  amber: {
    bg: 'bg-gradient-to-br from-amber-400 to-orange-500',
    iconBg: 'bg-amber-100',
    iconColor: 'text-amber-600',
    trendUp: 'bg-orange-100 text-orange-700',
    trendDown: 'bg-amber-100 text-amber-700',
  },
  green: {
    bg: 'bg-gradient-to-br from-green-400 to-emerald-500',
    iconBg: 'bg-green-100',
    iconColor: 'text-green-600',
    trendUp: 'bg-emerald-100 text-emerald-700',
    trendDown: 'bg-green-100 text-green-700',
  },
  purple: {
    bg: 'bg-gradient-to-br from-purple-400 to-pink-500',
    iconBg: 'bg-purple-100',
    iconColor: 'text-purple-600',
    trendUp: 'bg-pink-100 text-pink-700',
    trendDown: 'bg-purple-100 text-purple-700',
  },
  cyan: {
    bg: 'bg-gradient-to-br from-cyan-400 to-blue-500',
    iconBg: 'bg-cyan-100',
    iconColor: 'text-cyan-600',
    trendUp: 'bg-blue-100 text-blue-700',
    trendDown: 'bg-cyan-100 text-cyan-700',
  },
};

export default function StatCard({ icon: Icon, label, value, trend, trendUp, color }: StatCardProps) {
  const [displayValue, setDisplayValue] = useState<number | string>(0);
  const colors = colorClasses[color];

  useEffect(() => {
    if (typeof value === 'number') {
      let start = 0;
      const end = value;
      const duration = 1000;
      const increment = end / (duration / 16);

      const timer = setInterval(() => {
        start += increment;
        if (start >= end) {
          setDisplayValue(end);
          clearInterval(timer);
        } else {
          setDisplayValue(Math.floor(start));
        }
      }, 16);

      return () => clearInterval(timer);
    } else {
      setDisplayValue(value);
    }
  }, [value]);

  return (
    <motion.div
      className="relative rounded-2xl p-1 shadow-lg hover:shadow-xl transition-all duration-300 group cursor-pointer overflow-hidden"
      whileHover={{ y: -4, scale: 1.02 }}
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3 }}
    >
      {/* Gradient background */}
      <div className={`absolute inset-0 ${colors.bg} opacity-90 group-hover:opacity-100 transition-opacity`} />
      
      {/* Content */}
      <div className="relative z-10 bg-white/90 backdrop-blur-sm rounded-xl p-5 group-hover:bg-white/95 transition-all">
        <div className="flex items-start justify-between mb-3">
          <div className={`w-12 h-12 ${colors.iconBg} rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform duration-300`}>
            <Icon className={`w-6 h-6 ${colors.iconColor}`} />
          </div>
          <div className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs font-bold ${
            trendUp ? colors.trendUp : colors.trendDown
          }`}>
            {trendUp ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
            {trend}
          </div>
        </div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
        >
          <p className="text-2xl font-bold text-gray-800 mb-1">
            {displayValue}
          </p>
          <p className="text-sm text-gray-600 font-medium">{label}</p>
        </motion.div>
      </div>
    </motion.div>
  );
}
// src/components/RiskChart.tsx - ENHANCED
import { motion } from 'framer-motion';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';

interface RiskChartProps {
  data?: Array<{ name: string; value: number; color: string }>;
}

const defaultData = [
  { name: 'Low Risk', value: 45, color: '#10B981' },
  { name: 'Medium Risk', value: 25, color: '#F59E0B' },
  { name: 'High Risk', value: 20, color: '#EF4444' },
  { name: 'Critical', value: 10, color: '#7C3AED' },
];

export default function RiskChart({ data = defaultData }: RiskChartProps) {
  return (
    <div className="bg-white rounded-2xl p-6 shadow-lg border border-gray-100">
      <h3 className="font-semibold text-gray-800 mb-6 text-lg">Risk Distribution</h3>
      
      <div className="flex items-center justify-center">
        <div className="w-48 h-48">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={80}
                paddingAngle={2}
                dataKey="value"
              >
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="space-y-3 mt-6">
        {data.map((item, index) => (
          <motion.div
            key={item.name}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.1 }}
            className="flex items-center justify-between p-3 hover:bg-gray-50 rounded-lg transition-colors"
          >
            <div className="flex items-center space-x-3">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: item.color }}
              />
              <span className="font-medium text-gray-700">{item.name}</span>
            </div>
            <span className="font-semibold text-gray-900">{item.value}%</span>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
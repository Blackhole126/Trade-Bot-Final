export const DashboardSkeleton = () => (
  <div className="space-y-4 animate-pulse">
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {[1, 2, 3].map((i) => (
        <div key={i} className="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-slate-700 rounded"></div>
            <div className="w-16 h-6 bg-slate-700 rounded"></div>
          </div>
          <div className="w-20 h-3 bg-slate-700 rounded mb-2"></div>
          <div className="w-32 h-8 bg-slate-700 rounded"></div>
        </div>
      ))}
    </div>
    <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
      <div className="w-40 h-6 bg-slate-700 rounded mb-4"></div>
      <div className="h-64 bg-slate-700 rounded"></div>
    </div>
  </div>
);

export const PredictionCardSkeleton = () => (
  <div className="bg-slate-700/50 rounded-lg border border-slate-600/50 p-3 animate-pulse">
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-3 flex-1">
        <div className="w-12 h-12 bg-slate-600 rounded-lg"></div>
        <div className="flex-1">
          <div className="w-20 h-5 bg-slate-600 rounded mb-2"></div>
          <div className="w-24 h-4 bg-slate-600 rounded"></div>
        </div>
      </div>
      <div className="w-16 h-6 bg-slate-600 rounded"></div>
    </div>
  </div>
);

export const TableSkeleton = () => (
  <div className="animate-pulse">
    <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
      <div className="p-4 border-b border-slate-700">
        <div className="w-32 h-5 bg-slate-700 rounded"></div>
      </div>
      <div className="divide-y divide-slate-700">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="p-4">
            <div className="flex items-center justify-between">
              <div className="w-24 h-4 bg-slate-700 rounded"></div>
              <div className="w-16 h-4 bg-slate-700 rounded"></div>
              <div className="w-20 h-4 bg-slate-700 rounded"></div>
              <div className="w-16 h-4 bg-slate-700 rounded"></div>
            </div>
          </div>
        ))}
      </div>
    </div>
  </div>
);





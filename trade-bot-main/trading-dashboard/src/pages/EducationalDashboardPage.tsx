import React from 'react';
import Layout from '../components/Layout';
import { FeatureUnavailable } from '../components/FeatureUnavailable';

const EducationalDashboardPage = () => {
  return (
    <Layout>
      <div className="space-y-6 animate-fadeIn w-full">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2">
          <div className="flex-1 min-w-0">
            <h1 className="text-xl md:text-2xl font-bold text-white">Financial Education Center</h1>
            <p className="text-gray-400 text-sm">
              Learn trading fundamentals through our Gurukul-style pedagogy system
            </p>
          </div>
        </div>
        
        <FeatureUnavailable
          feature="Educational Modules"
          reason="This feature requires backend support and is currently unavailable."
          suggestion="Backend does not implement /api/education endpoints. Educational content requires server-side implementation."
          mode="info"
        />
      </div>
    </Layout>
  );
};

export default EducationalDashboardPage;
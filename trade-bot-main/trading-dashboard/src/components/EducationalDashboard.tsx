import React, { useState } from 'react';
import { BookOpen, Brain, Lightbulb, Users, Eye, Zap, Trophy, Award, GraduationCap, Target, Shield, TrendingUp, DollarSign, Activity } from 'lucide-react';
import { usePortfolio } from '../contexts/PortfolioContext';

interface EducationalLevel {
  id: 'seed' | 'tree' | 'sky';
  name: string;
  icon: React.ReactNode;
  description: string;
  features: string[];
  restrictions: string[];
  learningObjectives: string[];
  assessmentCriteria: string[];
  educationalResources: string[];
  riskManagementFocus: string[];
}



const EDUCATIONAL_LEVELS: EducationalLevel[] = [
  {
    id: 'seed',
    name: 'Seed Level',
    icon: <BookOpen className="w-5 h-5" />,
    description: 'Beginner learning phase - foundational concepts',
    features: [
      'Basic market overview',
      'Simple price charts',
      'Fundamental indicators',
      'Risk education modules',
      'Learning assessments'
    ],
    restrictions: [
      'Limited to 1-2 stocks',
      'Maximum 100 shares per trade',
      'No leverage allowed',
      'Mandatory learning modules'
    ],
    learningObjectives: [
      'Understand basic market concepts',
      'Learn fundamental analysis',
      'Recognize risk factors',
      'Develop disciplined approach'
    ],
    assessmentCriteria: [
      'Complete 5 basic lessons',
      'Pass 80% quiz score',
      'Simulate 10 trades',
      'Maintain 70% accuracy'
    ],
    educationalResources: [
      'Market Basics Course',
      'Risk Management Guide',
      'Investment Psychology',
      'Technical Analysis Fundamentals'
    ],
    riskManagementFocus: [
      'Capital Preservation',
      'Position Sizing',
      'Stop Loss Discipline',
      'Emotional Control'
    ]
  },
  {
    id: 'tree',
    name: 'Tree Level',
    icon: <Brain className="w-5 h-5" />,
    description: 'Intermediate practice phase - behavioral learning',
    features: [
      'Advanced charting tools',
      'Technical indicators',
      'Portfolio tracking',
      'Risk management tools',
      'Practice trading'
    ],
    restrictions: [
      'Maximum 5 stocks',
      'Up to 500 shares per trade',
      'Limited leverage (2x)',
      'Weekly activity limits'
    ],
    learningObjectives: [
      'Master technical analysis',
      'Implement risk management',
      'Develop trading strategy',
      'Analyze market trends'
    ],
    assessmentCriteria: [
      'Complete 10 advanced lessons',
      'Pass 85% quiz score',
      'Execute 50 simulated trades',
      'Maintain 75% accuracy'
    ],
    educationalResources: [
      'Technical Analysis Masterclass',
      'Risk Management Workshop',
      'Strategy Development Course',
      'Market Psychology Seminar'
    ],
    riskManagementFocus: [
      'Advanced Position Sizing',
      'Portfolio Diversification',
      'Risk-Reward Optimization',
      'Volatility Management'
    ]
  },
  {
    id: 'sky',
    name: 'Sky Level',
    icon: <Lightbulb className="w-5 h-5" />,
    description: 'Advanced analysis phase - multi-factor analysis',
    features: [
      'All trading tools',
      'Advanced analytics',
      'Custom indicators',
      'Automated strategies',
      'Professional features'
    ],
    restrictions: [
      'Full market access',
      'Higher volume trades',
      'Advanced leverage',
      'Professional oversight'
    ],
    learningObjectives: [
      'Master algorithmic trading',
      'Implement advanced strategies',
      'Conduct market research',
      'Optimize performance'
    ],
    assessmentCriteria: [
      'Complete 15 expert lessons',
      'Pass 90% quiz score',
      'Execute 100 live trades',
      'Maintain 80% accuracy'
    ],
    educationalResources: [
      'Algorithmic Trading Systems',
      'Quantitative Analysis',
      'Advanced Risk Models',
      'Professional Trading Strategies'
    ],
    riskManagementFocus: [
      'Institutional Risk Controls',
      'Regulatory Compliance',
      'Large Position Management',
      'Systematic Risk Assessment'
    ]
  }
];

const EducationalDashboard: React.FC = () => {
  const { portfolioState, selectPortfolio } = usePortfolio();
  const [activeTab, setActiveTab] = useState<'overview' | 'features' | 'progress'>('overview');

  const currentLevel = EDUCATIONAL_LEVELS.find(level => level.id === portfolioState.selectedPortfolio) || EDUCATIONAL_LEVELS[0];

  return (
    <div className="space-y-6">
      {/* Level Selector */}
      <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
        <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
          <Users className="w-5 h-5" />
          Learning Pathway
        </h2>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          {EDUCATIONAL_LEVELS.map((level) => (
            <div
              key={level.id}
              onClick={() => selectPortfolio(level.id)}
              className={`p-4 rounded-lg border cursor-pointer transition-all duration-200 ${
                portfolioState.selectedPortfolio === level.id
                  ? 'border-blue-500 bg-blue-500/10'
                  : 'border-slate-600 hover:border-slate-500 bg-slate-700/30'
              }`}
            >
              <div className="flex items-center gap-2 mb-2">
                {level.icon}
                <span className="font-semibold text-white">{level.name}</span>
              </div>
              <p className="text-sm text-slate-300">{level.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Current Level Info */}
      <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-blue-500/20 rounded-lg">
            {currentLevel.icon}
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">{currentLevel.name}</h3>
            <p className="text-sm text-slate-400">{currentLevel.description}</p>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex space-x-1 mb-4 bg-slate-700/50 rounded-lg p-1">
          {(['overview', 'features', 'progress'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex-1 py-2 px-3 rounded-md text-sm font-medium transition-colors ${
                activeTab === tab
                  ? 'bg-blue-500 text-white'
                  : 'text-slate-300 hover:text-white'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="space-y-4">
          {activeTab === 'overview' && (
            <div>
              <h4 className="font-semibold text-white mb-3">Level Overview</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <h5 className="text-sm font-medium text-slate-300 mb-2 flex items-center gap-1">
                    <Eye className="w-4 h-4" />
                    Available Features
                  </h5>
                  <ul className="space-y-1">
                    {currentLevel.features.map((feature, index) => (
                      <li key={index} className="text-sm text-slate-400 flex items-center gap-2">
                        <div className="w-1.5 h-1.5 bg-green-500 rounded-full"></div>
                        {feature}
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h5 className="text-sm font-medium text-slate-300 mb-2 flex items-center gap-1">
                    <Zap className="w-4 h-4" />
                    Restrictions
                  </h5>
                  <ul className="space-y-1">
                                    {currentLevel.restrictions?.map((restriction, index) => (
                      <li key={index} className="text-sm text-slate-400 flex items-center gap-2">
                        <div className="w-1.5 h-1.5 bg-red-500 rounded-full"></div>
                        {restriction}
                      </li>
                    )) || []}
                  </ul>
                </div>
              </div>
              
              <div className="mt-4 pt-4 border-t border-slate-700">
                <h5 className="text-sm font-medium text-slate-300 mb-2 flex items-center gap-1">
                  <Target className="w-4 h-4" />
                  Learning Objectives
                </h5>
                <ul className="space-y-1">
                  {currentLevel.learningObjectives.map((objective, index) => (
                    <li key={index} className="text-sm text-slate-400 flex items-center gap-2">
                      <div className="w-1.5 h-1.5 bg-blue-500 rounded-full"></div>
                      {objective}
                    </li>
                  ))}
                </ul>
              </div>
              
              <div className="mt-4 pt-4 border-t border-slate-700">
                <h5 className="text-sm font-medium text-slate-300 mb-2 flex items-center gap-1">
                  <Shield className="w-4 h-4" />
                  Risk Management Focus
                </h5>
                <ul className="space-y-1">
                  {currentLevel.riskManagementFocus.map((focus, index) => (
                    <li key={index} className="text-sm text-slate-400 flex items-center gap-2">
                      <div className="w-1.5 h-1.5 bg-yellow-500 rounded-full"></div>
                      {focus}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {activeTab === 'features' && (
            <div>
              <h4 className="font-semibold text-white mb-3">Detailed Features</h4>
              <div className="space-y-3">
                {currentLevel.features.map((feature, index) => (
                  <div key={index} className="p-3 bg-slate-700/30 rounded-lg">
                    <div className="flex items-center gap-2 mb-1">
                      <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                      <span className="font-medium text-white">{feature}</span>
                    </div>
                    <p className="text-xs text-slate-400 ml-6">
                      {feature.toLowerCase().includes('learning') && 'Complete learning modules to unlock advanced features'}
                      {feature.toLowerCase().includes('risk') && 'Understand risk concepts before accessing tools'}
                      {feature.toLowerCase().includes('portfolio') && 'Track your progress and learning achievements'}
                    </p>
                  </div>
                ))}
              </div>
              
              <div className="mt-6">
                <h4 className="font-semibold text-white mb-3 flex items-center gap-2">
                  <GraduationCap className="w-4 h-4" />
                  Educational Resources
                </h4>
                <div className="space-y-2">
                  {currentLevel.educationalResources.map((resource, index) => (
                    <div key={index} className="p-3 bg-slate-700/30 rounded-lg flex items-center gap-2">
                      <Award className="w-4 h-4 text-blue-400" />
                      <span className="text-white">{resource}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'progress' && (
            <div>
              <h4 className="font-semibold text-white mb-3">Learning Progress</h4>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-slate-300">Concept Mastery</span>
                    <span className="text-white">65%</span>
                  </div>
                  <div className="w-full bg-slate-700 rounded-full h-2">
                    <div className="bg-blue-500 h-2 rounded-full" style={{ width: '65%' }}></div>
                  </div>
                </div>
                
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-slate-300">Practical Skills</span>
                    <span className="text-white">42%</span>
                  </div>
                  <div className="w-full bg-slate-700 rounded-full h-2">
                    <div className="bg-green-500 h-2 rounded-full" style={{ width: '42%' }}></div>
                  </div>
                </div>
                
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-slate-300">Risk Awareness</span>
                    <span className="text-white">78%</span>
                  </div>
                  <div className="w-full bg-slate-700 rounded-full h-2">
                    <div className="bg-yellow-500 h-2 rounded-full" style={{ width: '78%' }}></div>
                  </div>
                </div>
              </div>
              
              <div className="mt-4 p-3 bg-slate-700/30 rounded-lg">
                <h5 className="font-medium text-white mb-2 flex items-center gap-2">
                  <Trophy className="w-4 h-4" />
                  Assessment Criteria
                </h5>
                <ul className="space-y-2">
                  {currentLevel.assessmentCriteria.map((criterion, index) => (
                    <li key={index} className="flex items-center gap-2 text-sm">
                      <div className={`w-2 h-2 rounded-full ${index < 2 ? 'bg-green-500' : 'bg-slate-600'}`}></div>
                      <span className="text-slate-300">{criterion}</span>
                      {index < 2 && <div className="ml-auto text-xs text-green-400">✓ Completed</div>}
                    </li>
                  ))}
                </ul>
              </div>
              
              <div className="mt-4 p-3 bg-slate-700/30 rounded-lg">
                <h5 className="font-medium text-white mb-2">Next Milestone</h5>
                <p className="text-sm text-slate-300">
                  Complete "Risk Management Fundamentals" to unlock advanced charting tools
                </p>
                <button className="mt-2 w-full py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-md text-sm font-medium transition-colors">
                  Start Learning Module
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Educational Resources */}
      <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Learning Resources</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[
            { title: 'Market Basics', desc: 'Understanding stock markets', level: 'seed' },
            { title: 'Risk Management', desc: 'Protecting your capital', level: 'tree' },
            { title: 'Advanced Strategies', desc: 'Professional techniques', level: 'sky' },
            { title: 'Psychology of Trading', desc: 'Emotional discipline', level: 'tree' },
            { title: 'Technical Analysis', desc: 'Chart patterns', level: 'tree' },
            { title: 'Portfolio Theory', desc: 'Diversification', level: 'sky' }
          ].map((resource, index) => (
            <div key={index} className={`p-4 rounded-lg border ${
              currentLevel.id === resource.level
                ? 'border-blue-500 bg-blue-500/10'
                : 'border-slate-600 bg-slate-700/30'
            }`}>
              <h4 className="font-medium text-white mb-1">{resource.title}</h4>
              <p className="text-sm text-slate-400 mb-2">{resource.desc}</p>
              <span className={`inline-block px-2 py-1 rounded-full text-xs ${
                currentLevel.id === resource.level
                  ? 'bg-blue-500/20 text-blue-400'
                  : 'bg-slate-600 text-slate-400'
              }`}>
                {resource.level.charAt(0).toUpperCase() + resource.level.slice(1)} Level
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default EducationalDashboard;
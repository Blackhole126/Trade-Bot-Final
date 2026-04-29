import React, { useState, useEffect } from 'react';
import { BookOpen, Brain, Lightbulb, Users, Eye, Zap, Trophy, Award, GraduationCap, Target, Shield, TrendingUp, DollarSign, Activity, BarChart3, PieChart, LineChart, Briefcase } from 'lucide-react';
import { usePortfolio } from '../contexts/PortfolioContext';
import { educationalAPI } from '../services/api';
import { useNotification } from '../contexts/NotificationContext';

interface EducationalResource {
  id: string;
  title: string;
  description: string;
  level: 'seed' | 'tree' | 'sky';
  duration: string;
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  completed: boolean;
}

interface LearningModule {
  id: string;
  title: string;
  description: string;
  level: 'seed' | 'tree' | 'sky';
  lessons: number;
  duration: string;
  progress: number;
  icon: React.ReactNode;
}

const EducationalHub: React.FC = () => {
  const { portfolioState } = usePortfolio();
  const { showNotification } = useNotification();
  const [activeTab, setActiveTab] = useState<'modules' | 'resources' | 'progress' | 'assessments'>('modules');
  const [learningModules, setLearningModules] = useState<LearningModule[]>([]);
  const [educationalResources, setEducationalResources] = useState<EducationalResource[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadEducationalData();
  }, []);

  const loadEducationalData = async () => {
    setLoading(true);
    setError(null);
    try {
      // Fetch modules from backend
      const modulesResponse = await educationalAPI.getModules();
      setLearningModules(modulesResponse.modules || []);

      // Fetch resources from backend (or use a separate endpoint if available)
      // For now, we'll use the same response or fallback to empty array
      setEducationalResources(modulesResponse.resources || []);
      
      showNotification('success', 'Education Data Loaded', 'Learning materials updated from server');
    } catch (err: any) {
      console.error('Failed to load educational data:', err);
      setError(err.message || 'Failed to load educational content');
      showNotification('error', 'Load Failed', 'Could not fetch educational content. Showing demo data.');
      
      // Fallback to original hardcoded data
      setLearningModules([
        {
          id: 'basics',
          title: 'Market Fundamentals',
          description: 'Understanding the basics of financial markets and instruments',
          level: 'seed',
          lessons: 10,
          duration: '2 hours',
          progress: 75,
          icon: <BookOpen className="w-5 h-5" />
        },
        {
          id: 'psychology',
          title: 'Investment Psychology',
          description: 'Managing emotions and cognitive biases in decision-making',
          level: 'seed',
          lessons: 8,
          duration: '1.5 hours',
          progress: 30,
          icon: <Users className="w-5 h-5" />
        },
        {
          id: 'analysis',
          title: 'Technical Analysis',
          description: 'Learning chart patterns and indicators for market analysis',
          level: 'tree',
          lessons: 15,
          duration: '4 hours',
          progress: 40,
          icon: <BarChart3 className="w-5 h-5" />
        },
        {
          id: 'fundamental',
          title: 'Fundamental Analysis',
          description: 'Analyzing company financials and economic indicators',
          level: 'tree',
          lessons: 12,
          duration: '3.5 hours',
          progress: 15,
          icon: <PieChart className="w-5 h-5" />
        },
        {
          id: 'risk',
          title: 'Risk Management',
          description: 'Capital preservation and position sizing strategies',
          level: 'tree',
          lessons: 12,
          duration: '3 hours',
          progress: 20,
          icon: <Shield className="w-5 h-5" />
        },
        {
          id: 'portfolio',
          title: 'Portfolio Theory',
          description: 'Diversification and asset allocation principles',
          level: 'sky',
          lessons: 18,
          duration: '6 hours',
          progress: 0,
          icon: <Briefcase className="w-5 h-5" />
        },
        {
          id: 'algo',
          title: 'Algorithmic Trading',
          description: 'Building and testing automated trading systems',
          level: 'sky',
          lessons: 20,
          duration: '8 hours',
          progress: 0,
          icon: <Activity className="w-5 h-5" />
        },
        {
          id: 'derivatives',
          title: 'Derivatives & Options',
          description: 'Advanced instruments for hedging and speculation',
          level: 'sky',
          lessons: 22,
          duration: '9 hours',
          progress: 0,
          icon: <Zap className="w-5 h-5" />
        }
      ]);

      setEducationalResources([
        {
          id: 'intro-video',
          title: 'Introduction to Financial Markets',
          description: 'Overview of market structures and instruments',
          level: 'seed',
          duration: '30 mins',
          difficulty: 'beginner',
          completed: true
        },
        {
          id: 'psychology-basics',
          title: 'Investment Psychology Fundamentals',
          description: 'Understanding emotional biases in decision-making',
          level: 'seed',
          duration: '25 mins',
          difficulty: 'beginner',
          completed: false
        },
        {
          id: 'chart-patterns',
          title: 'Technical Analysis Patterns',
          description: 'Recognizing common chart patterns and formations',
          level: 'tree',
          duration: '45 mins',
          difficulty: 'intermediate',
          completed: false
        },
        {
          id: 'fundamental-analysis',
          title: 'Fundamental Analysis Basics',
          description: 'Reading financial statements and ratios',
          level: 'tree',
          duration: '50 mins',
          difficulty: 'intermediate',
          completed: false
        },
        {
          id: 'risk-strategies',
          title: 'Risk Management Framework',
          description: 'Strategies for capital preservation and position sizing',
          level: 'tree',
          duration: '60 mins',
          difficulty: 'intermediate',
          completed: false
        },
        {
          id: 'portfolio-theory',
          title: 'Modern Portfolio Theory',
          description: 'Principles of diversification and asset allocation',
          level: 'sky',
          duration: '75 mins',
          difficulty: 'advanced',
          completed: false
        },
        {
          id: 'algorithmic-trading',
          title: 'Algorithmic Trading Systems',
          description: 'Building and backtesting automated strategies',
          level: 'sky',
          duration: '90 mins',
          difficulty: 'advanced',
          completed: false
        },
        {
          id: 'derivatives',
          title: 'Options and Derivatives',
          description: 'Advanced instruments for hedging and speculation',
          level: 'sky',
          duration: '85 mins',
          difficulty: 'advanced',
          completed: false
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  // Handler to mark a lesson as completed
  const handleMarkComplete = async (moduleId: string, resourceId: string) => {
    try {
      await educationalAPI.saveProgress(moduleId, 100, true);
      showNotification('success', 'Lesson Completed', 'Your progress has been saved to the server');
      
      // Update local state to reflect completion
      setEducationalResources(prev => 
        prev.map(resource => 
          resource.id === resourceId 
            ? { ...resource, completed: true } 
            : resource
        )
      );
    } catch (err: any) {
      console.error('Failed to save progress:', err);
      showNotification('error', 'Save Failed', 'Could not save your progress to the server');
    }
  };

  // Get current level info
  const currentLevel = learningModules.find(module => module.level === portfolioState.selectedPortfolio) || learningModules[0];

  if (loading) {
    return (
      <div className="flex justify-center items-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        <span className="ml-2 text-gray-400">Loading educational content...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-900/30 border border-red-700 rounded-lg p-4 text-red-200">
        <p className="font-semibold mb-1">Error Loading Content</p>
        <p className="text-sm">{error}</p>
        <button 
          onClick={loadEducationalData}
          className="mt-3 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded text-sm"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Level Overview Card */}
      <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <GraduationCap className="w-6 h-6 text-blue-400" />
            Learning Pathway
          </h2>
          <div className="flex items-center gap-2">
            <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
              portfolioState.selectedPortfolio === 'seed' ? 'bg-green-500/20 text-green-400' :
              portfolioState.selectedPortfolio === 'tree' ? 'bg-blue-500/20 text-blue-400' :
              'bg-purple-500/20 text-purple-400'
            }`}>
              {portfolioState.selectedPortfolio === 'seed' ? 'Seed Level' :
               portfolioState.selectedPortfolio === 'tree' ? 'Tree Level' : 'Sky Level'}
            </span>
          </div>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className={`p-4 rounded-lg border ${
            portfolioState.selectedPortfolio === 'seed' 
              ? 'border-green-500 bg-green-500/10' 
              : 'border-slate-600 bg-slate-700/30 hover:border-slate-500 cursor-pointer'
          } transition-all duration-200`}
          onClick={() => portfolioState.selectedPortfolio !== 'seed' && console.log('Switch to seed')}>
            <div className="flex items-center gap-2 mb-2">
              <BookOpen className="w-5 h-5 text-green-400" />
              <span className="font-semibold text-white">Seed Level</span>
            </div>
            <p className="text-sm text-slate-300 mb-3">Foundation building and basic concepts</p>
            <div className="space-y-2">
              <div className="flex justify-between text-xs">
                <span className="text-slate-400">Progress</span>
                <span className="text-white">65%</span>
              </div>
              <div className="w-full bg-slate-700 rounded-full h-2">
                <div className="bg-green-500 h-2 rounded-full" style={{ width: '65%' }}></div>
              </div>
            </div>
          </div>
          
          <div className={`p-4 rounded-lg border ${
            portfolioState.selectedPortfolio === 'tree' 
              ? 'border-blue-500 bg-blue-500/10' 
              : 'border-slate-600 bg-slate-700/30 hover:border-slate-500 cursor-pointer'
          } transition-all duration-200`}
          onClick={() => portfolioState.selectedPortfolio !== 'tree' && console.log('Switch to tree')}>
            <div className="flex items-center gap-2 mb-2">
              <Brain className="w-5 h-5 text-blue-400" />
              <span className="font-semibold text-white">Tree Level</span>
            </div>
            <p className="text-sm text-slate-300 mb-3">Skill development and practical application</p>
            <div className="space-y-2">
              <div className="flex justify-between text-xs">
                <span className="text-slate-400">Progress</span>
                <span className="text-white">42%</span>
              </div>
              <div className="w-full bg-slate-700 rounded-full h-2">
                <div className="bg-blue-500 h-2 rounded-full" style={{ width: '42%' }}></div>
              </div>
            </div>
          </div>
          
          <div className={`p-4 rounded-lg border ${
            portfolioState.selectedPortfolio === 'sky' 
              ? 'border-purple-500 bg-purple-500/10' 
              : 'border-slate-600 bg-slate-700/30 hover:border-slate-500 cursor-pointer'
          } transition-all duration-200`}
          onClick={() => portfolioState.selectedPortfolio !== 'sky' && console.log('Switch to sky')}>
            <div className="flex items-center gap-2 mb-2">
              <Lightbulb className="w-5 h-5 text-purple-400" />
              <span className="font-semibold text-white">Sky Level</span>
            </div>
            <p className="text-sm text-slate-300 mb-3">Advanced strategies and professional techniques</p>
            <div className="space-y-2">
              <div className="flex justify-between text-xs">
                <span className="text-slate-400">Progress</span>
                <span className="text-white">18%</span>
              </div>
              <div className="w-full bg-slate-700 rounded-full h-2">
                <div className="bg-purple-500 h-2 rounded-full" style={{ width: '18%' }}></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl">
        <div className="flex border-b border-slate-700">
          {(['modules', 'resources', 'progress', 'assessments'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex-1 py-3 px-4 text-sm font-medium transition-colors ${
                activeTab === tab
                  ? 'bg-slate-700/50 text-white border-b-2 border-blue-500'
                  : 'text-slate-400 hover:text-white hover:bg-slate-700/30'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>

        <div className="p-6">
          {/* Learning Modules Tab */}
          {activeTab === 'modules' && (
            <div>
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <BookOpen className="w-5 h-5" />
                Learning Modules
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {learningModules.map((module) => (
                  <div key={module.id} className="bg-slate-700/30 rounded-lg p-4 border border-slate-600 hover:border-slate-500 transition-colors">
                    <div className="flex items-start gap-3">
                      <div className={`p-2 rounded-lg ${
                        module.level === 'seed' ? 'bg-green-500/20 text-green-400' :
                        module.level === 'tree' ? 'bg-blue-500/20 text-blue-400' :
                        'bg-purple-500/20 text-purple-400'
                      }`}>
                        {module.icon}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-1">
                          <h4 className="font-medium text-white">{module.title}</h4>
                          <span className={`text-xs px-2 py-1 rounded ${
                            module.level === 'seed' ? 'bg-green-500/20 text-green-400' :
                            module.level === 'tree' ? 'bg-blue-500/20 text-blue-400' :
                            'bg-purple-500/20 text-purple-400'
                          }`}>
                            {module.level === 'seed' ? 'Seed' : module.level === 'tree' ? 'Tree' : 'Sky'}
                          </span>
                        </div>
                        <p className="text-sm text-slate-400 mb-3">{module.description}</p>
                        <div className="flex items-center justify-between text-xs text-slate-500 mb-2">
                          <span>{module.lessons} lessons</span>
                          <span>{module.duration}</span>
                        </div>
                        <div className="space-y-2">
                          <div className="flex justify-between text-xs">
                            <span className="text-slate-400">Progress</span>
                            <span className="text-white">{module.progress}%</span>
                          </div>
                          <div className="w-full bg-slate-600 rounded-full h-2">
                            <div 
                              className={`h-2 rounded-full ${
                                module.level === 'seed' ? 'bg-green-500' :
                                module.level === 'tree' ? 'bg-blue-500' :
                                'bg-purple-500'
                              }`}
                              style={{ width: `${module.progress}%` }}
                            ></div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Resources Tab */}
          {activeTab === 'resources' && (
            <div>
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <Award className="w-5 h-5" />
                Educational Resources
              </h3>
              <div className="space-y-4">
                {educationalResources.map((resource) => (
                  <div key={resource.id} className="bg-slate-700/30 rounded-lg p-4 border border-slate-600 hover:border-slate-500 transition-colors">
                    <div className="flex items-start gap-4">
                      <div className={`p-2 rounded-lg ${
                        resource.level === 'seed' ? 'bg-green-500/20 text-green-400' :
                        resource.level === 'tree' ? 'bg-blue-500/20 text-blue-400' :
                        'bg-purple-500/20 text-purple-400'
                      }`}>
                        <GraduationCap className="w-5 h-5" />
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-1">
                          <h4 className="font-medium text-white">{resource.title}</h4>
                          <div className="flex items-center gap-2">
                            <span className={`text-xs px-2 py-1 rounded ${
                              resource.difficulty === 'beginner' ? 'bg-green-500/20 text-green-400' :
                              resource.difficulty === 'intermediate' ? 'bg-yellow-500/20 text-yellow-400' :
                              'bg-red-500/20 text-red-400'
                            }`}>
                              {resource.difficulty}
                            </span>
                            {resource.completed && (
                              <span className="text-green-400 text-xs">✓ Completed</span>
                            )}
                          </div>
                        </div>
                        <p className="text-sm text-slate-400 mb-2">{resource.description}</p>
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-slate-500">{resource.duration}</span>
                          <button 
                            onClick={() => handleMarkComplete(resource.level, resource.id)}
                            className={`px-3 py-1 rounded text-xs font-medium ${
                              resource.completed 
                                ? 'bg-green-500/20 text-green-400' 
                                : 'bg-blue-500 hover:bg-blue-600 text-white'
                            }`}
                          >
                            {resource.completed ? 'Review' : 'Start'}
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Progress Tab */}
          {activeTab === 'progress' && (
            <div>
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <TrendingUp className="w-5 h-5" />
                Learning Progress
              </h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                <div className="bg-slate-700/30 rounded-lg p-4 border border-slate-600">
                  <h4 className="font-medium text-white mb-3">Overall Progress</h4>
                  <div className="space-y-4">
                    <div>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-slate-300">Total Completion</span>
                        <span className="text-white">52%</span>
                      </div>
                      <div className="w-full bg-slate-600 rounded-full h-3">
                        <div className="bg-gradient-to-r from-blue-500 to-purple-500 h-3 rounded-full" style={{ width: '52%' }}></div>
                      </div>
                    </div>
                    
                    <div>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-slate-300">Modules Completed</span>
                        <span className="text-white">12/24</span>
                      </div>
                      <div className="w-full bg-slate-600 rounded-full h-2">
                        <div className="bg-green-500 h-2 rounded-full" style={{ width: '50%' }}></div>
                      </div>
                    </div>
                    
                    <div>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-slate-300">Assessments Passed</span>
                        <span className="text-white">8/10</span>
                      </div>
                      <div className="w-full bg-slate-600 rounded-full h-2">
                        <div className="bg-yellow-500 h-2 rounded-full" style={{ width: '80%' }}></div>
                      </div>
                    </div>
                  </div>
                </div>
                
                <div className="bg-slate-700/30 rounded-lg p-4 border border-slate-600">
                  <h4 className="font-medium text-white mb-3">Level Progress</h4>
                  <div className="space-y-3">
                    <div>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-green-400">Seed Level</span>
                        <span className="text-white">65%</span>
                      </div>
                      <div className="w-full bg-slate-600 rounded-full h-2">
                        <div className="bg-green-500 h-2 rounded-full" style={{ width: '65%' }}></div>
                      </div>
                    </div>
                    
                    <div>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-blue-400">Tree Level</span>
                        <span className="text-white">42%</span>
                      </div>
                      <div className="w-full bg-slate-600 rounded-full h-2">
                        <div className="bg-blue-500 h-2 rounded-full" style={{ width: '42%' }}></div>
                      </div>
                    </div>
                    
                    <div>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-purple-400">Sky Level</span>
                        <span className="text-white">18%</span>
                      </div>
                      <div className="w-full bg-slate-600 rounded-full h-2">
                        <div className="bg-purple-500 h-2 rounded-full" style={{ width: '18%' }}></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              
              <div className="bg-slate-700/30 rounded-lg p-4 border border-slate-600">
                <h4 className="font-medium text-white mb-3">Recent Achievements</h4>
                <div className="space-y-3">
                  <div className="flex items-center gap-3 p-3 bg-slate-600/30 rounded-lg">
                    <Trophy className="w-5 h-5 text-yellow-400" />
                    <div>
                      <p className="text-white font-medium">Market Basics Certified</p>
                      <p className="text-slate-400 text-sm">Completed Introduction to Trading course</p>
                    </div>
                    <span className="text-xs text-slate-500 ml-auto">2 days ago</span>
                  </div>
                  
                  <div className="flex items-center gap-3 p-3 bg-slate-600/30 rounded-lg">
                    <Award className="w-5 h-5 text-green-400" />
                    <div>
                      <p className="text-white font-medium">Risk Management Proficient</p>
                      <p className="text-slate-400 text-sm">Passed Risk Assessment Module</p>
                    </div>
                    <span className="text-xs text-slate-500 ml-auto">1 week ago</span>
                  </div>
                  
                  <div className="flex items-center gap-3 p-3 bg-slate-600/30 rounded-lg">
                    <Target className="w-5 h-5 text-blue-400" />
                    <div>
                      <p className="text-white font-medium">Technical Analysis Beginner</p>
                      <p className="text-slate-400 text-sm">Completed Chart Patterns Module</p>
                    </div>
                    <span className="text-xs text-slate-500 ml-auto">2 weeks ago</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Assessments Tab */}
          {activeTab === 'assessments' && (
            <div>
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <Target className="w-5 h-5" />
                Assessments & Quizzes
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-slate-700/30 rounded-lg p-4 border border-slate-600">
                  <div className="flex items-center gap-2 mb-3">
                    <Shield className="w-5 h-5 text-green-400" />
                    <h4 className="font-medium text-white">Seed Level: Market Fundamentals</h4>
                  </div>
                  <p className="text-sm text-slate-400 mb-4">Assessment of basic market knowledge and investment principles</p>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs text-slate-500">Questions: 15</p>
                      <p className="text-xs text-slate-500">Time Limit: 20 min</p>
                    </div>
                    <button className="px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg text-sm font-medium transition-colors">
                      Start Assessment
                    </button>
                  </div>
                </div>
                
                <div className="bg-slate-700/30 rounded-lg p-4 border border-slate-600">
                  <div className="flex items-center gap-2 mb-3">
                    <BarChart3 className="w-5 h-5 text-blue-400" />
                    <h4 className="font-medium text-white">Tree Level: Technical Analysis</h4>
                  </div>
                  <p className="text-sm text-slate-400 mb-4">Assessment of chart patterns, indicators and market analysis</p>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs text-slate-500">Questions: 20</p>
                      <p className="text-xs text-slate-500">Time Limit: 35 min</p>
                    </div>
                    <button className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm font-medium transition-colors">
                      Start Assessment
                    </button>
                  </div>
                </div>
                
                <div className="bg-slate-700/30 rounded-lg p-4 border border-slate-600">
                  <div className="flex items-center gap-2 mb-3">
                    <PieChart className="w-5 h-5 text-purple-400" />
                    <h4 className="font-medium text-white">Sky Level: Advanced Portfolio Management</h4>
                  </div>
                  <p className="text-sm text-slate-400 mb-4">Comprehensive exam on portfolio theory and advanced strategies</p>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs text-slate-500">Questions: 25</p>
                      <p className="text-xs text-slate-500">Time Limit: 50 min</p>
                    </div>
                    <button className="px-4 py-2 bg-purple-500 hover:bg-purple-600 text-white rounded-lg text-sm font-medium transition-colors">
                      Start Exam
                    </button>
                  </div>
                </div>
                
                <div className="bg-slate-700/30 rounded-lg p-4 border border-slate-600">
                  <div className="flex items-center gap-2 mb-3">
                    <LineChart className="w-5 h-5 text-purple-400" />
                    <h4 className="font-medium text-white">Sky Level: Algorithmic Strategies</h4>
                  </div>
                  <p className="text-sm text-slate-400 mb-4">Advanced quiz on algorithmic trading and quantitative methods</p>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs text-slate-500">Questions: 30</p>
                      <p className="text-xs text-slate-500">Time Limit: 60 min</p>
                    </div>
                    <button className="px-4 py-2 bg-purple-500 hover:bg-purple-600 text-white rounded-lg text-sm font-medium transition-colors">
                      Start Assessment
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Educational Insights */}
      <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Activity className="w-5 h-5" />
          Market Education Insights
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-slate-700/30 rounded-lg p-4 border border-slate-600">
            <div className="flex items-center gap-2 mb-2">
              <DollarSign className="w-5 h-5 text-green-400" />
              <h4 className="font-medium text-white">Capital Preservation</h4>
            </div>
            <p className="text-sm text-slate-400">Always risk no more than 1-2% of your capital per trade to protect your investment portfolio.</p>
          </div>
          
          <div className="bg-slate-700/30 rounded-lg p-4 border border-slate-600">
            <div className="flex items-center gap-2 mb-2">
              <Shield className="w-5 h-5 text-blue-400" />
              <h4 className="font-medium text-white">Stop-Loss Strategy</h4>
            </div>
            <p className="text-sm text-slate-400">Set stop-loss orders at 5-8% below your entry price to limit potential losses.</p>
          </div>
          
          <div className="bg-slate-700/30 rounded-lg p-4 border border-slate-600">
            <div className="flex items-center gap-2 mb-2">
              <TrendingUp className="w-5 h-5 text-purple-400" />
              <h4 className="font-medium text-white">Risk-Reward Ratio</h4>
            </div>
            <p className="text-sm text-slate-400">Aim for a minimum 1:2 risk-reward ratio to ensure profitable trading over time.</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EducationalHub;
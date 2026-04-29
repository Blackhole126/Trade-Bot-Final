/**
 * Export utilities for exporting data to CSV, JSON, and PDF formats
 */

import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';
import html2canvas from 'html2canvas';
import { format } from 'date-fns';

export interface ExportableData {
  [key: string]: any;
}

/**
 * Export data to CSV format
 */
export const exportToCSV = (data: any[], filename: string = 'export.csv'): void => {
  if (data.length === 0) {
    alert('No data to export');
    return;
  }

  // Get headers from first object
  const headers = Object.keys(data[0]);

  // Create CSV content
  const csvContent = [
    headers.join(','),
    ...data.map(row =>
      headers.map(header => {
        const value = row[header];
        // Handle values that might contain commas or quotes
        if (value === null || value === undefined) return '';
        const stringValue = String(value);
        if (stringValue.includes(',') || stringValue.includes('"') || stringValue.includes('\n')) {
          return `"${stringValue.replace(/"/g, '""')}"`;
        }
        return stringValue;
      }).join(',')
    )
  ].join('\n');

  // Create blob and download
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
};

/**
 * Export data to JSON format
 */
export const exportToJSON = (data: any, filename: string = 'export.json'): void => {
  const jsonContent = JSON.stringify(data, null, 2);
  const blob = new Blob([jsonContent], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
};

/**
 * Export data to PDF format
 */
export const exportToPDF = async (
  data: any[],
  title: string = 'Export Report',
  filename: string = `export-${format(new Date(), 'yyyy-MM-dd')}.pdf`,
  columns?: string[]
): Promise<void> => {
  if (data.length === 0) {
    alert('No data to export');
    return;
  }

  try {
    const doc = new jsPDF();

    // Add title
    doc.setFontSize(18);
    doc.text(title, 14, 20);

    // Add date
    doc.setFontSize(10);
    doc.text(`Generated: ${format(new Date(), 'PPpp')}`, 14, 30);

    // Get headers
    const headers = columns || Object.keys(data[0]);

    // Prepare table data
    const tableData = data.map(row =>
      headers.map(header => {
        const value = row[header];
        if (value === null || value === undefined) return '';
        if (typeof value === 'number') {
          return value.toFixed(2);
        }
        return String(value);
      })
    );

    // Add table
    autoTable(doc, {
      head: [headers],
      body: tableData,
      startY: 35,
      styles: { fontSize: 8 },
      headStyles: { fillColor: [37, 99, 235] }, // Blue color
    });

    // Save PDF
    doc.save(filename);
  } catch (error) {
    console.error('Failed to export PDF:', error);
    alert('Failed to export PDF. Please try again.');
  }
};

/**
 * Export HTML element as PDF image
 */
export const exportHTMLToPDF = async (
  elementId: string,
  filename: string = `export-${format(new Date(), 'yyyy-MM-dd')}.pdf`,
  title?: string
): Promise<void> => {
  try {
    const element = document.getElementById(elementId);
    if (!element) {
      alert('Element not found');
      return;
    }

    const canvas = await html2canvas(element, {
      scale: 2,
      useCORS: true,
      logging: false,
    });

    const imgData = canvas.toDataURL('image/png');
    const pdf = new jsPDF('p', 'mm', 'a4');
    const imgWidth = 210;
    const pageHeight = 295;
    const imgHeight = (canvas.height * imgWidth) / canvas.width;
    let heightLeft = imgHeight;

    let position = 0;

    // Add title if provided
    if (title) {
      pdf.setFontSize(18);
      pdf.text(title, 10, 20);
      position = 30;
      heightLeft = imgHeight - 10;
    }

    pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
    heightLeft -= pageHeight;

    while (heightLeft >= 0) {
      position = heightLeft - imgHeight;
      pdf.addPage();
      pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
      heightLeft -= pageHeight;
    }

    pdf.save(filename);
  } catch (error) {
    console.error('Failed to export HTML to PDF:', error);
    alert('Failed to export to PDF. Please try again.');
  }
};

/**
 * Email export data (opens mailto link)
 */
export const exportViaEmail = (data: any[], subject: string = 'Trading Data Export'): void => {
  if (data.length === 0) {
    alert('No data to export');
    return;
  }

  // Convert to CSV for email
  const headers = Object.keys(data[0]);
  const csvContent = [
    headers.join(','),
    ...data.map(row =>
      headers.map(header => {
        const value = row[header];
        if (value === null || value === undefined) return '';
        const stringValue = String(value);
        if (stringValue.includes(',') || stringValue.includes('"')) {
          return `"${stringValue.replace(/"/g, '""')}"`;
        }
        return stringValue;
      }).join(',')
    )
  ].join('\n');

  // Create mailto link
  const body = encodeURIComponent(`Please find the attached trading data export.\n\n${csvContent}`);
  const mailtoLink = `mailto:?subject=${encodeURIComponent(subject)}&body=${body}`;

  window.location.href = mailtoLink;
};

/**
 * Schedule export (saves to localStorage for scheduled execution)
 */
export const scheduleExport = (
  exportFunction: () => void,
  scheduleTime: Date,
  label: string = 'Scheduled Export'
): void => {
  const scheduledExports = JSON.parse(localStorage.getItem('scheduledExports') || '[]');

  scheduledExports.push({
    id: Date.now().toString(),
    label,
    executeAt: scheduleTime.toISOString(),
    functionName: exportFunction.name,
  });

  localStorage.setItem('scheduledExports', JSON.stringify(scheduledExports));
  alert(`Export scheduled for ${format(scheduleTime, 'PPpp')}`);
};

/**
 * Export portfolio to CSV
 */
export const exportPortfolio = (holdings: any[]): void => {
  const data = holdings.map(holding => ({
    Symbol: holding.symbol,
    Shares: holding.shares,
    'Avg Price': holding.avgPrice?.toFixed(2) || '0.00',
    'Current Price': holding.currentPrice?.toFixed(2) || '0.00',
    Value: holding.value?.toFixed(2) || '0.00',
    'Gain/Loss': ((holding.currentPrice - holding.avgPrice) * holding.shares).toFixed(2),
    'Gain/Loss %': (((holding.currentPrice - holding.avgPrice) / holding.avgPrice) * 100).toFixed(2) + '%',
  }));
  exportToCSV(data, `portfolio-${format(new Date(), 'yyyy-MM-dd')}.csv`);
};

/**
 * Export portfolio to PDF
 */
export const exportPortfolioToPDF = async (holdings: any[]): Promise<void> => {
  const data = holdings.map(holding => ({
    Symbol: holding.symbol,
    Shares: holding.shares,
    'Avg Price': `₹${holding.avgPrice?.toFixed(2) || '0.00'}`,
    'Current Price': `₹${holding.currentPrice?.toFixed(2) || '0.00'}`,
    Value: `₹${holding.value?.toFixed(2) || '0.00'}`,
    'Gain/Loss': `₹${((holding.currentPrice - holding.avgPrice) * holding.shares).toFixed(2)}`,
    'Gain/Loss %': `${(((holding.currentPrice - holding.avgPrice) / holding.avgPrice) * 100).toFixed(2)}%`,
  }));
  await exportToPDF(data, 'Portfolio Report', `portfolio-${format(new Date(), 'yyyy-MM-dd')}.pdf`);
};

/**
 * Export predictions to CSV
 */
export const exportPredictions = (predictions: any[]): void => {
  const data = predictions.map(pred => ({
    Symbol: pred.symbol,
    Action: pred.action,
    'Current Price': pred.current_price?.toFixed(2) || '0.00',
    'Predicted Price': pred.predicted_price?.toFixed(2) || '0.00',
    'Predicted Return %': (pred.predicted_return || 0).toFixed(2) + '%',
    Confidence: ((pred.confidence || 0) * 100).toFixed(0) + '%',
    Horizon: pred.horizon || 'N/A',
  }));
  exportToCSV(data, `predictions-${format(new Date(), 'yyyy-MM-dd')}.csv`);
};

/**
 * Export predictions to PDF
 */
export const exportPredictionsToPDF = async (predictions: any[]): Promise<void> => {
  const data = predictions.map(pred => ({
    Symbol: pred.symbol,
    Action: pred.action,
    'Current Price': `₹${pred.current_price?.toFixed(2) || '0.00'}`,
    'Predicted Price': `₹${pred.predicted_price?.toFixed(2) || '0.00'}`,
    'Predicted Return %': `${(pred.predicted_return || 0).toFixed(2)}%`,
    Confidence: `${((pred.confidence || 0) * 100).toFixed(0)}%`,
    Horizon: pred.horizon || 'N/A',
  }));
  await exportToPDF(data, 'Predictions Report', `predictions-${format(new Date(), 'yyyy-MM-dd')}.pdf`);
};

/**
 * Copy text to clipboard
 */
export const copyToClipboard = async (text: string): Promise<boolean> => {
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    } else {
      // Fallback for older browsers
      const textArea = document.createElement('textarea');
      textArea.value = text;
      textArea.style.position = 'fixed';
      textArea.style.opacity = '0';
      document.body.appendChild(textArea);
      textArea.select();
      const success = document.execCommand('copy');
      document.body.removeChild(textArea);
      return success;
    }
  } catch (error) {
    console.error('Failed to copy to clipboard:', error);
    return false;
  }
};

/**
 * Format number as currency
 */
export const formatCurrency = (value: number, currency: string = 'INR'): string => {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: currency,
  }).format(value);
};

/**
 * Format number with commas
 */
export const formatNumber = (value: number, decimals: number = 2): string => {
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
};

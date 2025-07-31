from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.core.management import call_command
from django.utils import timezone
from django.contrib import messages
from django.db.models import Count, Avg, Q
import subprocess
import threading
import json
import sys
import os
import signal
from io import StringIO

from apps.portfolio.models import Trade, Portfolio, TradingAccount
from apps.market_data_service.models import (
    Company, TradingSignal, ValuationMetrics, 
    ProfitabilityMetrics, GrowthMetrics, QualitativeAnalysis,
    ShareholdingPattern, FinancialStatement, FundamentalScore
)
from .models import TaskExecution, DashboardWidget

# Global dictionary to track running processes
running_processes = {}

def dashboard_home(request):
    try:
        portfolio_metrics = get_portfolio_metrics()
        companies_data = get_scraped_companies_data()
        recent_trades = get_recent_trades()
        system_status = get_system_status()
        recent_tasks = TaskExecution.objects.all().order_by('-started_at')[:10]
        available_commands = get_available_commands()
        
        context = {
            'portfolio_metrics': portfolio_metrics,
            'companies_data': companies_data,
            'recent_trades': recent_trades,
            'system_status': system_status,
            'recent_tasks': recent_tasks,
            'available_commands': available_commands,
            'page_title': 'NSE Trading System Dashboard',
        }
        
        return render(request, 'dashboard/dashboard_home.html', context)
        
    except Exception as e:
        return render(request, 'dashboard/dashboard_home.html', {
            'error_message': f"Dashboard loading error: {str(e)}",
            'portfolio_metrics': get_default_portfolio_metrics(),
            'companies_data': {'companies': [], 'stats': {}},
            'recent_trades': [],
            'system_status': get_default_system_status(),
            'recent_tasks': [],
            'available_commands': get_available_commands(),
        })

def get_scraped_companies_data():
    try:
        companies = Company.objects.filter(
            is_active=True,
            last_scraped__isnull=False
        ).select_related(
            'industry_classification'
        ).prefetch_related(
            'valuation_metrics',
            'profitability_metrics', 
            'growth_metrics',
            'fundamental_scores'
        )[:20]
        
        companies_list = []
        for company in companies:
            valuation = getattr(company, 'valuation_metrics', None)
            profitability = getattr(company, 'profitability_metrics', None)
            growth = getattr(company, 'growth_metrics', None)
            score = company.fundamental_scores.first() if hasattr(company, 'fundamental_scores') else None
            
            company_data = {
                'symbol': company.symbol,
                'name': company.name,
                'industry': company.industry_classification.name if company.industry_classification else 'N/A',
                'last_scraped': company.last_scraped,
                'market_cap': float(valuation.market_cap) if valuation and valuation.market_cap else None,
                'current_price': float(valuation.current_price) if valuation and valuation.current_price else None,
                'pe_ratio': float(valuation.stock_pe) if valuation and valuation.stock_pe else None,
                'roe': float(profitability.roe) if profitability and profitability.roe else None,
                'roce': float(profitability.roce) if profitability and profitability.roce else None,
                'sales_growth_1y': float(growth.sales_growth_1y) if growth and growth.sales_growth_1y else None,
                'profit_growth_1y': float(growth.profit_growth_1y) if growth and growth.profit_growth_1y else None,
                'overall_score': float(score.overall_score) if score and score.overall_score else None,
                'website': company.website,
                'bse_code': company.bse_code,
                'nse_code': company.nse_code,
            }
            companies_list.append(company_data)
        
        total_companies = Company.objects.filter(is_active=True).count()
        scraped_companies = Company.objects.filter(
            is_active=True, 
            last_scraped__isnull=False
        ).count()
        
        industry_stats = Company.objects.filter(
            is_active=True,
            industry_classification__isnull=False
        ).values(
            'industry_classification__name'
        ).annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        avg_metrics = ValuationMetrics.objects.aggregate(
            avg_pe=Avg('stock_pe'),
            avg_market_cap=Avg('market_cap'),
            avg_dividend_yield=Avg('dividend_yield')
        )
        
        stats = {
            'total_companies': total_companies,
            'scraped_companies': scraped_companies,
            'coverage_percentage': round((scraped_companies / total_companies * 100) if total_companies > 0 else 0, 1),
            'top_industries': list(industry_stats),
            'avg_pe': round(float(avg_metrics['avg_pe']) if avg_metrics['avg_pe'] else 0, 2),
            'avg_market_cap': round(float(avg_metrics['avg_market_cap']) if avg_metrics['avg_market_cap'] else 0, 2),
            'avg_dividend_yield': round(float(avg_metrics['avg_dividend_yield']) if avg_metrics['avg_dividend_yield'] else 0, 2),
        }
        
        return {
            'companies': companies_list,
            'stats': stats
        }
        
    except Exception as e:
        return {
            'companies': [],
            'stats': {
                'total_companies': 0,
                'scraped_companies': 0,
                'coverage_percentage': 0,
                'top_industries': [],
                'avg_pe': 0,
                'avg_market_cap': 0,
                'avg_dividend_yield': 0,
            }
        }

def get_portfolio_metrics():
    try:
        account = TradingAccount.objects.filter(is_active=True).first()
        if account:
            portfolio_positions = Portfolio.objects.filter(account=account, position_status='OPEN')
            total_value = sum(pos.market_value for pos in portfolio_positions if pos.market_value)
            total_unrealized_pnl = sum(pos.unrealized_pnl for pos in portfolio_positions if pos.unrealized_pnl)
            return {
                'total_value': float(total_value) if total_value else 0.0,
                'daily_pnl': float(total_unrealized_pnl) if total_unrealized_pnl else 0.0,
                'total_pnl': float(account.total_pnl) if account.total_pnl else 0.0,
                'cash_balance': float(account.current_capital) if account.current_capital else 0.0,
                'positions_count': portfolio_positions.count(),
            }
        
        return get_default_portfolio_metrics()
    except Exception as e:
        return get_default_portfolio_metrics()

def get_default_portfolio_metrics():
    return {
        'total_value': 0.0,
        'daily_pnl': 0.0,
        'total_pnl': 0.0,
        'cash_balance': 0.0,
        'positions_count': 0,
    }

def get_recent_trades():
    try:
        return Trade.objects.filter(
            created_at__gte=timezone.now() - timezone.timedelta(days=7)
        ).order_by('-created_at')[:10]
    except Exception as e:
        return []

def get_system_status():
    try:
        pending_trades = Trade.objects.filter(status='PENDING').count() if Trade.objects.exists() else 0
        active_companies = Company.objects.filter(is_active=True).count()
        recent_scrapes = Company.objects.filter(
            last_scraped__gte=timezone.now() - timezone.timedelta(hours=24)
        ).count()
        running_tasks = TaskExecution.objects.filter(status='running').count()
        
        return {
            'trading_engine': 'Active' if pending_trades >= 0 else 'Inactive',
            'market_data_feed': 'Connected' if active_companies > 0 else 'Disconnected',
            'last_update': timezone.now(),
            'pending_orders': pending_trades,
            'active_companies': active_companies,
            'recent_scrapes': recent_scrapes,
            'running_tasks': running_tasks,
        }
    except Exception as e:
        return get_default_system_status()

def get_default_system_status():
    return {
        'trading_engine': 'Unknown',
        'market_data_feed': 'Unknown',  
        'last_update': timezone.now(),
        'pending_orders': 0,
        'active_companies': 0,
        'recent_scrapes': 0,
        'running_tasks': 0,
    }

def get_companies_api(request):
    companies_data = get_scraped_companies_data()
    return JsonResponse(companies_data)

def get_company_details(request, symbol):
    try:
        company = Company.objects.select_related(
            'industry_classification'
        ).prefetch_related(
            'valuation_metrics',
            'profitability_metrics',
            'growth_metrics',
            'qualitative_analysis',
            'fundamental_scores'
        ).get(symbol=symbol)
        
        valuation = getattr(company, 'valuation_metrics', None)
        profitability = getattr(company, 'profitability_metrics', None)
        growth = getattr(company, 'growth_metrics', None)
        qualitative = company.qualitative_analysis.first() if hasattr(company, 'qualitative_analysis') else None
        score = company.fundamental_scores.first() if hasattr(company, 'fundamental_scores') else None
        
        company_details = {
            'basic_info': {
                'symbol': company.symbol,
                'name': company.name,
                'about': company.about,
                'website': company.website,
                'industry': company.industry_classification.name if company.industry_classification else None,
                'bse_code': company.bse_code,
                'nse_code': company.nse_code,
                'last_scraped': company.last_scraped.isoformat() if company.last_scraped else None,
            },
            'valuation_metrics': {
                'market_cap': float(valuation.market_cap) if valuation and valuation.market_cap else None,
                'current_price': float(valuation.current_price) if valuation and valuation.current_price else None,
                'stock_pe': float(valuation.stock_pe) if valuation and valuation.stock_pe else None,
                'book_value': float(valuation.book_value) if valuation and valuation.book_value else None,
                'dividend_yield': float(valuation.dividend_yield) if valuation and valuation.dividend_yield else None,
                'high_52_week': float(valuation.high_52_week) if valuation and valuation.high_52_week else None,
                'low_52_week': float(valuation.low_52_week) if valuation and valuation.low_52_week else None,
            } if valuation else {},
            'profitability_metrics': {
                'roe': float(profitability.roe) if profitability and profitability.roe else None,
                'roce': float(profitability.roce) if profitability and profitability.roce else None,
            } if profitability else {},
            'growth_metrics': {
                'sales_growth_1y': float(growth.sales_growth_1y) if growth and growth.sales_growth_1y else None,
                'sales_growth_3y': float(growth.sales_growth_3y) if growth and growth.sales_growth_3y else None,
                'sales_growth_5y': float(growth.sales_growth_5y) if growth and growth.sales_growth_5y else None,
                'profit_growth_1y': float(growth.profit_growth_1y) if growth and growth.profit_growth_1y else None,
                'profit_growth_3y': float(growth.profit_growth_3y) if growth and growth.profit_growth_3y else None,
                'profit_growth_5y': float(growth.profit_growth_5y) if growth and growth.profit_growth_5y else None,
            } if growth else {},
            'qualitative_analysis': {
                'pros': qualitative.pros if qualitative else [],
                'cons': qualitative.cons if qualitative else [],
            } if qualitative else {},
            'fundamental_scores': {
                'overall_score': float(score.overall_score) if score and score.overall_score else None,
                'valuation_score': float(score.valuation_score) if score and score.valuation_score else None,
                'profitability_score': float(score.profitability_score) if score and score.profitability_score else None,
                'growth_score': float(score.growth_score) if score and score.growth_score else None,
            } if score else {},
        }
        
        return JsonResponse(company_details)
        
    except Company.DoesNotExist:
        return JsonResponse({'error': 'Company not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def execute_task(request):
    if request.method == 'POST':
        task_name = request.POST.get('task_name')
        command = request.POST.get('command')
        parameters = request.POST.get('parameters', '{}')
        
        try:
            parameters_dict = json.loads(parameters) if parameters.strip() else {}
        except json.JSONDecodeError:
            parameters_dict = {}
        
        task_execution = TaskExecution.objects.create(
            task_name=task_name,
            command=command,
            parameters=parameters_dict,
            executed_by=None,
            status='pending'
        )
        
        thread = threading.Thread(
            target=run_task_async,
            args=(task_execution.id, command, parameters_dict)
        )
        thread.daemon = True
        thread.start()
        
        messages.success(request, f'Task "{task_name}" started successfully! Task ID: {task_execution.id}')
        return redirect('dashboard:home')
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

def run_task_async(task_id, command, parameters):
    process = None
    try:
        task_execution = TaskExecution.objects.get(id=task_id)
        task_execution.status = 'running'
        task_execution.save()
        
        output_lines = []
        
        if command.startswith('manage.py'):
            cmd_parts = command.split()[1:]
            full_command = [sys.executable, 'manage.py'] + cmd_parts
        else:
            full_command = command.split()
        
        # Start the process
        process = subprocess.Popen(
            full_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            cwd=os.getcwd()
        )
        
        # Store process in global dict for potential termination
        running_processes[task_id] = process
        
        # Read output line by line and update database
        for line in iter(process.stdout.readline, ''):
            if line:
                output_lines.append(line.strip())
                # Update task with current output every 10 lines
                if len(output_lines) % 10 == 0:
                    current_output = '\n'.join(output_lines)
                    task_execution.output = current_output
                    task_execution.save()
        
        # Wait for process to complete
        process.wait()
        
        # Final output update
        final_output = '\n'.join(output_lines)
        if not final_output.strip():
            final_output = "Command executed successfully with no output."
        
        # Remove from running processes
        if task_id in running_processes:
            del running_processes[task_id]
        
        # Check return code
        if process.returncode == 0:
            task_execution.status = 'completed'
        else:
            task_execution.status = 'failed'
            final_output += f"\n\nProcess exited with code: {process.returncode}"
        
        task_execution.output = final_output
        task_execution.completed_at = timezone.now()
        
    except Exception as e:
        error_msg = f"Task execution failed: {str(e)}"
        try:
            task_execution = TaskExecution.objects.get(id=task_id)
            task_execution.status = 'failed'
            task_execution.error_log = error_msg
            task_execution.completed_at = timezone.now()
            task_execution.save()
        except:
            pass
        
        # Clean up process if it exists
        if process and process.poll() is None:
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                try:
                    process.kill()
                except:
                    pass
        
        # Remove from running processes
        if task_id in running_processes:
            del running_processes[task_id]
    
    try:
        task_execution.save()
    except Exception as e:
        pass

def stop_task(request, task_id):
    try:
        task_execution = TaskExecution.objects.get(id=task_id)
        
        if task_execution.status != 'running':
            return JsonResponse({
                'success': False, 
                'message': f'Task is not running (status: {task_execution.status})'
            })
        
        # Try to terminate the process
        if task_id in running_processes:
            process = running_processes[task_id]
            try:
                # First try graceful termination
                process.terminate()
                
                # Wait up to 5 seconds for graceful shutdown
                try:
                    process.wait(timeout=5)
                    termination_method = "terminated gracefully"
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't terminate gracefully
                    process.kill()
                    process.wait()
                    termination_method = "force killed"
                
                # Update task status
                task_execution.status = 'stopped'
                task_execution.completed_at = timezone.now()
                current_output = task_execution.output or ""
                task_execution.output = current_output + f"\n\n--- TASK STOPPED BY USER ({termination_method}) ---"
                task_execution.save()
                
                # Remove from running processes
                del running_processes[task_id]
                
                return JsonResponse({
                    'success': True, 
                    'message': f'Task stopped successfully ({termination_method})'
                })
                
            except Exception as e:
                return JsonResponse({
                    'success': False, 
                    'message': f'Failed to stop task: {str(e)}'
                })
        else:
            # Process not found in running_processes, just update status
            task_execution.status = 'stopped'
            task_execution.completed_at = timezone.now()
            current_output = task_execution.output or ""
            task_execution.output = current_output + "\n\n--- TASK STOPPED (process not found) ---"
            task_execution.save()
            
            return JsonResponse({
                'success': True, 
                'message': 'Task marked as stopped'
            })
            
    except TaskExecution.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Task not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

def get_available_commands():
    return [
        {
            'name': 'Scrape Fundamentals',
            'command': 'manage.py scrape_fundamentals',
            'description': 'Scrape company fundamental data from Screener.in',
            'category': 'Data'
        },
        {
            'name': 'Update Market Data',
            'command': 'manage.py collect_market_data',
            'description': 'Fetch latest market data from Fyers API',
            'category': 'Data'
        },
        {
            'name': 'Run Fundamental Analysis',
            'command': 'manage.py run_fundamental_analysis',
            'description': 'Execute fundamental analysis for all companies',
            'category': 'Analysis'
        },
        {
            'name': 'Generate Trading Signals',
            'command': 'manage.py generate_trading_signals',
            'description': 'Generate trading signals based on analysis',
            'category': 'Trading'
        },
    ]

def task_status(request, task_id):
    try:
        task = TaskExecution.objects.get(id=task_id)
        return JsonResponse({
            'status': task.status,
            'output': task.output,
            'error_log': task.error_log,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
            'started_at': task.started_at.isoformat() if task.started_at else None,
            'can_stop': task.status == 'running',
        })
    except TaskExecution.DoesNotExist:
        return JsonResponse({'error': 'Task not found'}, status=404)

def get_live_output(request, task_id):
    try:
        task = TaskExecution.objects.get(id=task_id)
        return JsonResponse({
            'output': task.output or '',
            'status': task.status,
            'last_update': task.updated_at.isoformat() if hasattr(task, 'updated_at') else None,
        })
    except TaskExecution.DoesNotExist:
        return JsonResponse({'error': 'Task not found'}, status=404)

def get_portfolio_performance(request):
    try:
        trades = Trade.objects.filter(
            created_at__gte=timezone.now() - timezone.timedelta(days=30)
        ).order_by('created_at')
        
        if not trades.exists():
            return JsonResponse({
                'dates': [],
                'values': [],
                'pnl': [],
            })
        
        chart_data = {
            'dates': [trade.created_at.strftime('%Y-%m-%d') for trade in trades],
            'values': [float(trade.quantity * trade.price) for trade in trades],
            'pnl': [float(trade.realized_pnl) if trade.realized_pnl else 0 for trade in trades],
        }
        
        return JsonResponse(chart_data)
    except Exception as e:
        return JsonResponse({'error': str(e)})

def get_recent_signals(request):
    try:
        signals = TradingSignal.objects.filter(
            created_at__gte=timezone.now() - timezone.timedelta(days=7)
        ).order_by('-created_at')[:10]
        
        signals_data = []
        for signal in signals:
            signals_data.append({
                'symbol': signal.symbol,
                'action': signal.signal_type,
                'confidence': float(signal.confidence) if signal.confidence else 0,
                'price': float(signal.target_price) if signal.target_price else 0,
                'created_at': signal.created_at.isoformat(),
                'signal_type': signal.analysis_type,
            })
        
        return JsonResponse({'signals': signals_data})
    except Exception as e:
        return JsonResponse({'error': str(e)})

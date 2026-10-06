<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Honeypot Security</title>
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        primary: '#6366f1',
                        secondary: '#4f46e5',
                        dark: '#1e293b',
                    },
                    fontFamily: {
                        sans: ['Inter', 'sans-serif'],
                    }
                }
            }
        }
    </script>
    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <!-- Font Awesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    
    <style>
        body { font-family: 'Inter', sans-serif; }
        .glass-panel {
            background: rgba(255, 255, 255, 0.7);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.5);
        }
        .sidebar-link {
            transition: all 0.2s ease-in-out;
        }
        .sidebar-link:hover, .sidebar-link.active {
            background-color: #eff6ff;
            color: #4f46e5;
            border-right: 3px solid #4f46e5;
        }
    </style>
</head>
<body class="bg-gray-50 text-slate-800">

    <div class="flex h-screen overflow-hidden">
        
        <!-- Sidebar -->
        <aside class="w-64 bg-white border-r border-gray-200 hidden md:flex flex-col z-20">
            <div class="h-16 flex items-center px-6 border-b border-gray-200">
                <div class="flex items-center gap-2 font-bold text-xl text-indigo-600">
                    <i class="fa-solid fa-shield-halved"></i>
                    <span>HoneyCom</span>
                </div>
            </div>

            <div class="flex-1 overflow-y-auto py-4">
                <nav class="space-y-1 px-3">
                    <a href="dashboard.php" class="sidebar-link active flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-gray-700">
                        <i class="fa-solid fa-chart-line w-5 text-center"></i>
                        Dashboard
                    </a>
                    <a href="index.php" class="sidebar-link flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-gray-700">
                        <i class="fa-solid fa-home w-5 text-center"></i>
                        Home
                    </a>
                    <a href="mining.php" class="sidebar-link flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-gray-700">
                        <i class="fa-solid fa-bug w-5 text-center"></i>
                        Data Mining
                    </a>
                    <a href="#" class="sidebar-link flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-gray-700">
                        <i class="fa-solid fa-list w-5 text-center"></i>
                        Logs
                    </a>
                     <a href="#" class="sidebar-link flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-gray-700">
                        <i class="fa-solid fa-gears w-5 text-center"></i>
                        Settings
                    </a>
                </nav>
            </div>

            <div class="p-4 border-t border-gray-200">
                <div class="flex items-center gap-3">
                    <div class="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-600 font-bold text-xs">
                        A
                    </div>
                    <div>
                        <p class="text-sm font-medium">Admin User</p>
                        <p class="text-xs text-gray-500">System Admin</p>
                    </div>
                </div>
            </div>
        </aside>

        <!-- Main Content Wrapper -->
        <div class="flex-1 flex flex-col h-full overflow-hidden relative">
            
            <!-- Top Header -->
            <header class="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6 z-10">
                <button class="md:hidden text-gray-500 hover:text-gray-700">
                    <i class="fa-solid fa-bars text-xl"></i>
                </button>
                
                <div class="flex items-center gap-4 ml-auto">
                    <div class="relative">
                        <span class="absolute top-0 right-0 w-2 h-2 bg-red-500 rounded-full border border-white"></span>
                        <i class="fa-regular fa-bell text-gray-500 text-lg cursor-pointer hover:text-indigo-600 transition"></i>
                    </div>
                    <div class="w-px h-6 bg-gray-200"></div>
                    <a href="docs/QUICKSTART.md" class="text-sm font-medium text-gray-600 hover:text-indigo-600">Documentation</a>
                </div>
            </header>

            <!-- Main Scrollable Content -->
            <main class="flex-1 overflow-x-hidden overflow-y-auto bg-gray-50 p-6">

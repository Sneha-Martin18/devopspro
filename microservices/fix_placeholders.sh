#!/bin/bash

# Remove existing directories
rm -rf placeholders/academic.html
rm -rf placeholders/attendance.html  
rm -rf placeholders/notification.html

# Create academic.html
cat > placeholders/academic.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>Academic Service - Placeholder</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
        .container { max-width: 600px; margin: 0 auto; }
        .status { color: #ff6b35; font-size: 24px; margin-bottom: 20px; }
        .info { color: #666; font-size: 16px; line-height: 1.6; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Academic Service</h1>
        <div class="status">🚧 Service Under Development</div>
        <div class="info">
            <p>This service will handle:</p>
            <ul style="text-align: left;">
                <li>Course management</li>
                <li>Subject management</li>
                <li>Session year management</li>
                <li>Enrollment management</li>
            </ul>
            <p><strong>Port:</strong> 8001</p>
            <p><strong>Status:</strong> Placeholder - To be implemented</p>
        </div>
    </div>
</body>
</html>
EOF

# Create attendance.html
cat > placeholders/attendance.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>Attendance Service - Placeholder</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
        .container { max-width: 600px; margin: 0 auto; }
        .status { color: #ff6b35; font-size: 24px; margin-bottom: 20px; }
        .info { color: #666; font-size: 16px; line-height: 1.6; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Attendance Service</h1>
        <div class="status">🚧 Service Under Development</div>
        <div class="info">
            <p>This service will handle:</p>
            <ul style="text-align: left;">
                <li>Attendance tracking</li>
                <li>Attendance reports</li>
                <li>Attendance analytics</li>
                <li>Student attendance history</li>
            </ul>
            <p><strong>Port:</strong> 8002</p>
            <p><strong>Status:</strong> Placeholder - To be implemented</p>
        </div>
    </div>
</body>
</html>
EOF

# Create notification.html
cat > placeholders/notification.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>Notification Service - Placeholder</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
        .container { max-width: 600px; margin: 0 auto; }
        .status { color: #ff6b35; font-size: 24px; margin-bottom: 20px; }
        .info { color: #666; font-size: 16px; line-height: 1.6; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Notification Service</h1>
        <div class="status">🚧 Service Under Development</div>
        <div class="info">
            <p>This service will handle:</p>
            <ul style="text-align: left;">
                <li>System notifications</li>
                <li>Email notifications</li>
                <li>Push notifications</li>
                <li>Notification history</li>
            </ul>
            <p><strong>Port:</strong> 8003</p>
            <p><strong>Status:</strong> Placeholder - To be implemented</p>
        </div>
    </div>
</body>
</html>
EOF

echo "Placeholder files created successfully!"

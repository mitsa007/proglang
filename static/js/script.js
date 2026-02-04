
document.addEventListener('DOMContentLoaded', function() {
    // Goal selection
    const goalOptions = document.querySelectorAll('.goal-option');
    const goalInput = document.getElementById('goal');

    goalOptions.forEach(option => {
        option.addEventListener('click', function() {
            goalOptions.forEach(opt => opt.classList.remove('active'));
            this.classList.add('active');
            goalInput.value = this.dataset.goal;
        });
    });

    // Charts
    const weeklyActivityCtx = document.getElementById('weeklyActivityChart');
    if (weeklyActivityCtx) {
        new Chart(weeklyActivityCtx, {
            type: 'bar',
            data: {
                labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                datasets: [{
                    label: 'Calories Burned',
                    data: [300, 450, 500, 600, 550, 700, 650],
                    backgroundColor: 'rgba(54, 162, 235, 0.6)',
                }]
            }
        });
    }

    const weightCtx = document.getElementById('weightChart');
    if (weightCtx) {
        new Chart(weightCtx, {
            type: 'line',
            data: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                datasets: [{
                    label: 'Weight (kg)',
                    data: [75, 74, 73, 72, 71, 70],
                    borderColor: 'rgba(255, 99, 132, 1)',
                    fill: false,
                }]
            }
        });
    }

    const workoutDurationCtx = document.getElementById('workoutDurationChart');
    if (workoutDurationCtx) {
        new Chart(workoutDurationCtx, {
            type: 'bar',
            data: {
                labels: ['Running', 'Cycling', 'Weightlifting', 'Yoga'],
                datasets: [{
                    label: 'Total Duration (mins)',
                    data: [120, 90, 150, 60],
                    backgroundColor: 'rgba(75, 192, 192, 0.6)',
                }]
            }
        });
    }
});

.PHONY: all install deps service enable start stop status clean

# Name of your service
SERVICE=remotePi
SERVICE_FILE=Init_SystemD_Files/$(SERVICE).service
SYSTEMD_PATH=/etc/systemd/system/$(SERVICE).service

all: install

install: deps service enable start

# Install Python dependencies
# If requirements.txt does not exist, this step will be skipped gracefully
deps:
	@if [ -f requirements.txt ]; then \
		pip3 install -r requirements.txt; \
	else \
		echo "No requirements.txt found, skipping Python dependency installation."; \
	fi

# Copy the systemd service file to the correct location and reload systemd
service:
	sudo cp $(SERVICE_FILE) $(SYSTEMD_PATH)
	sudo systemctl daemon-reload
	echo "Service file installed to $(SYSTEMD_PATH) and systemd reloaded."

# Enable the service to start on boot
enable:
	sudo systemctl enable $(SERVICE)

# Start the service
start:
	sudo systemctl start $(SERVICE)

# Stop the service
stop:
	sudo systemctl stop $(SERVICE)

# Show the status of the service
status:
	sudo systemctl status $(SERVICE)

# Remove the service from systemd and clean up
clean:
	-@sudo systemctl stop $(SERVICE)
	-@sudo systemctl disable $(SERVICE)
	-@sudo rm -f $(SYSTEMD_PATH)
	sudo systemctl daemon-reload
	echo "Service $(SERVICE) removed from systemd." 
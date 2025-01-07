# Airfield Info Server

A Django-based REST API server that provides detailed information about airports worldwide, including real-time timezone data.

## Features

- Comprehensive airport information (IATA codes, coordinates, elevation, etc.)
- Real-time timezone data via Google Maps API
- Regular data updates from OurAirports database
- RESTful API endpoints with JSON responses
- CORS support for cross-origin requests
- No authentication required for API access

## Setup

1. Clone the repository:
```bash
git clone https://github.com/Consiliency/Airfield-Info-Server.git
cd Airfield-Info-Server
```

2. Install dependencies using Poetry:
```bash
poetry install
```

3. Set up environment variables in `.env`:
```env
DEBUG=True
SECRET_KEY=your_secret_key
DATABASE_URL=postgres://user:password@localhost:5432/airfield_info
ALLOWED_HOSTS=localhost,127.0.0.1
GOOGLE_MAPS_API_KEY=your_google_maps_api_key  # Only needed for timezone updates
```

4. Run migrations:
```bash
poetry run python manage.py migrate
```

5. Start the development server:
```bash
poetry run python manage.py runserver
```

## API Endpoints

The API endpoints are publicly accessible and do not require authentication or API keys. The Google Maps API key is only used server-side for updating timezone information.

### Get Airport by IATA Code

```
GET /api/airports/by_iata/?code={iata_code}&include_timezone=true
```

Parameters:
- `code` (required): IATA airport code (e.g., LAX, JFK)
- `include_timezone` (optional): Set to "true" to include current timezone information

Example Request:
```bash
curl "http://localhost:8000/api/airports/by_iata/?code=LAX&include_timezone=true"
```

Example Response:
```json
{
    "id": "3484",
    "ident": "KLAX",
    "iata_code": "LAX",
    "name": "Los Angeles International Airport",
    "type": "large_airport",
    "latitude": "33.942501",
    "longitude": "-118.407997",
    "elevation_ft": 125.0,
    "continent": "NA",
    "iso_country": "US",
    "iso_region": "US-CA",
    "municipality": "Los Angeles",
    "scheduled_service": true,
    "gps_code": "KLAX",
    "local_code": "LAX",
    "home_link": "https://www.flylax.com/",
    "wikipedia_link": "https://en.wikipedia.org/wiki/Los_Angeles_International_Airport",
    "keywords": "Tom Bradley",
    "timezone": {
        "timezone_id": "America/Los_Angeles",
        "timezone_name": "Pacific Standard Time",
        "raw_offset": -28800,
        "dst_offset": 0,
        "total_offset": -8.0,
        "last_updated": "2025-01-07T20:50:22.543487Z"
    },
    "updated": "2025-01-07T20:50:22.543487Z"
}
```

### Get Airport by ICAO Code

```
GET /api/airports/by_icao/?code={icao_code}&include_timezone=true
```

Parameters:
- `code` (required): ICAO airport code (e.g., KLAX, KJFK)
- `include_timezone` (optional): Set to "true" to include current timezone information

Example Request:
```bash
curl "http://localhost:8000/api/airports/by_icao/?code=KLAX&include_timezone=true"
```

Response format is the same as the IATA endpoint.

## Data Updates

The server automatically checks for updates from the OurAirports database every 7 days. The data source is:
```
https://davidmegginson.github.io/ourairports-data/airports.csv
```

## Timezone Information

- Timezone data is fetched from the Google Maps Time Zone API (server-side only)
- Timezone information is cached and updated every 90 days
- The `total_offset` field includes both the raw UTC offset and any DST offset
- Times are returned in ISO 8601 format with UTC timezone

## Development

1. Install development dependencies:
```bash
poetry install --with dev
```

2. Run tests:
```bash
poetry run python manage.py test
```

## Deployment

### AWS Deployment Guide

1. **Set up AWS Account and CLI**
   - Create an AWS account if you don't have one
   - Install AWS CLI and configure credentials:
   ```bash
   aws configure
   ```

2. **Set up AWS Elastic Beanstalk**
   - Install EB CLI:
   ```bash
   pip install awsebcli
   ```
   - Initialize EB project:
   ```bash
   eb init -p python-3.10 airfield-info-server
   ```

3. **Create Required AWS Files**

Create `.ebextensions/01_packages.config`:
```yaml
packages:
  yum:
    postgresql-devel: []
    python3-devel: []
    gcc: []
```

Create `.ebextensions/02_python.config`:
```yaml
option_settings:
  aws:elasticbeanstalk:container:python:
    WSGIPath: config.wsgi:application
  aws:elasticbeanstalk:environment:proxy:staticfiles:
    /static: staticfiles
```

Create `Procfile`:
```
web: gunicorn config.wsgi --bind 0.0.0.0:8000
```

4. **Update Dependencies**
   ```bash
   poetry add gunicorn
   poetry export -f requirements.txt --output requirements.txt --without-hashes
   ```

5. **Configure Production Settings**

Create `config/production.py`:
```python
from .settings import *

DEBUG = False
ALLOWED_HOSTS = ['your-eb-url.elasticbeanstalk.com', 'your-domain.com']

# Configure static files for S3
AWS_STORAGE_BUCKET_NAME = 'your-bucket-name'
AWS_S3_REGION_NAME = 'your-region'
AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'

# Configure database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ['RDS_DB_NAME'],
        'USER': os.environ['RDS_USERNAME'],
        'PASSWORD': os.environ['RDS_PASSWORD'],
        'HOST': os.environ['RDS_HOSTNAME'],
        'PORT': os.environ['RDS_PORT'],
    }
}
```

6. **Create Elastic Beanstalk Environment**
   ```bash
   eb create airfield-info-prod --database --database.engine postgres
   ```

7. **Configure Environment Variables**
   - Go to AWS Elastic Beanstalk Console
   - Select your environment
   - Go to Configuration → Software
   - Add environment variables:
     - `DJANGO_SETTINGS_MODULE=config.production`
     - `GOOGLE_MAPS_API_KEY=your-key`
     - `SECRET_KEY=your-secret-key`

8. **Deploy Application**
   ```bash
   eb deploy
   ```

### Continuous Deployment with GitHub Actions

1. **Configure AWS Credentials**
   - Go to AWS IAM Console
   - Create a new IAM user for GitHub Actions
   - Add the `AWSElasticBeanstalkFullAccess` policy
   - Save the Access Key ID and Secret Access Key

2. **Set up GitHub Secrets**
   - Go to your GitHub repository settings
   - Navigate to Secrets and Variables → Actions
   - Add the following secrets:
     - `AWS_ACCESS_KEY_ID`
     - `AWS_SECRET_ACCESS_KEY`
     - `AWS_REGION`

3. **Create GitHub Actions Workflow**
   Create `.github/workflows/deploy.yml`:
   ```yaml
   name: Deploy to AWS Elastic Beanstalk
   
   on:
     push:
       branches: [ main ]
   
   jobs:
     deploy:
       runs-on: ubuntu-latest
       
       steps:
       - uses: actions/checkout@v2
       
       - name: Set up Python
         uses: actions/setup-python@v2
         with:
           python-version: '3.10'
       
       - name: Install dependencies
         run: |
           python -m pip install --upgrade pip
           pip install poetry
           poetry export -f requirements.txt --output requirements.txt --without-hashes
       
       - name: Deploy to EB
         uses: einaregilsson/beanstalk-deploy@v21
         with:
           aws_access_key: ${{ secrets.AWS_ACCESS_KEY_ID }}
           aws_secret_key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
           application_name: airfield-info-server
           environment_name: airfield-info-prod
           region: ${{ secrets.AWS_REGION }}
           deployment_package: .
   ```

Now your application will automatically deploy to AWS Elastic Beanstalk whenever you push to the main branch.

### Domain Configuration (GoDaddy to AWS)

1. **Get Elastic Beanstalk Domain**
   - Note your EB URL (e.g., `your-app.elasticbeanstalk.com`)

2. **Create Route 53 Hosted Zone**
   - Go to Route 53 in AWS Console
   - Create a hosted zone for your domain
   - Note the nameservers provided by AWS

3. **Update GoDaddy Nameservers**
   - Log in to GoDaddy
   - Go to Domain Settings → Nameservers
   - Select "Custom" and add AWS nameservers
   - Save changes (may take 24-48 hours to propagate)

4. **Configure DNS in Route 53**
   - Create an A record:
     - Name: @ (root domain)
     - Type: A
     - Alias: Yes
     - Target: Your Elastic Beanstalk environment
   - Create CNAME for www subdomain if needed

5. **Update Elastic Beanstalk Configuration**
   - Add your domain to ALLOWED_HOSTS in production settings
   - Update environment variables if needed
   - Deploy changes:
   ```bash
   eb deploy
   ```

### SSL Configuration

1. **Request SSL Certificate**
   - Go to AWS Certificate Manager
   - Request a certificate for your domain
   - Add both root and www versions
   - Verify ownership through DNS validation

2. **Configure Load Balancer**
   - In Elastic Beanstalk, modify environment configuration
   - Add HTTPS listener on port 443
   - Select your SSL certificate
   - Force HTTPS by redirecting HTTP to HTTPS

### Monitoring and Maintenance

- Set up CloudWatch alarms for monitoring
- Configure automatic backups for RDS database
- Set up S3 lifecycle policies for logs
- Enable AWS X-Ray for performance monitoring

## Environment Variables (Production)

Additional environment variables for production:
- `DJANGO_SETTINGS_MODULE`: Set to 'config.production'
- `RDS_DB_NAME`: PostgreSQL database name
- `RDS_USERNAME`: Database username
- `RDS_PASSWORD`: Database password
- `RDS_HOSTNAME`: Database host
- `RDS_PORT`: Database port
- `AWS_ACCESS_KEY_ID`: AWS access key
- `AWS_SECRET_ACCESS_KEY`: AWS secret key
- `AWS_STORAGE_BUCKET_NAME`: S3 bucket for static files

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Deployment to AWS

### Step 1: Set Up an AWS Account
- Create an AWS account if you haven't already.

### Step 2: Choose a Hosting Service
- Use AWS Elastic Beanstalk for easy deployment.

### Step 3: Install AWS CLI

#### For WSL (Ubuntu):
```bash
# Update package list and install prerequisites
sudo apt-get update
sudo apt-get install -y unzip curl

# Download the AWS CLI installation file
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"

# Unzip the installer
unzip awscliv2.zip

# Run the install program
sudo ./aws/install

# Verify the installation
aws --version
```

For other operating systems, download and install the AWS CLI from the [AWS CLI website](https://aws.amazon.com/cli/).

### Step 4: Configure AWS CLI

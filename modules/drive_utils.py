"""
Drive Utilities Module
Handles Google Drive API interactions.
"""

import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload


# Import scopes from auth service (unified with Calendar and Drive)
from services.auth import SCOPES as DRIVE_SCOPES

# Path to token file
TOKEN_FILE = os.path.join(os.path.dirname(__file__), '..', 'config', 'token.json')


def get_drive_service():
    """Get authenticated Google Drive service."""
    creds = None
    
    # Load existing credentials
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, DRIVE_SCOPES)
    
    # If no valid credentials, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            return None
        
        # Save credentials
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    
    try:
        return build('drive', 'v3', credentials=creds)
    except Exception:
        return None


def set_drive_file_public(file_id):
    """
    Set a Google Drive file to be publicly accessible.
    
    Args:
        file_id: The ID of the file to make public
    
    Returns:
        bool: True if successful, False otherwise
    """
    service = get_drive_service()
    
    if not service:
        return False
    
    try:
        # Create a permission that allows anyone with the link to view
        service.permissions().create(
            fileId=file_id,
            body={'type': 'anyone', 'role': 'reader'},
            sendNotificationEmail=False
        ).execute()
        return True
    except Exception as e:
        print(f"Error setting file permissions: {e}")
        return False


def upload_to_drive(file_name, file_content, mime_type=None):
    """
    Upload a file to Google Drive.
    
    Args:
        file_name: Name of the file
        file_content: Base64 encoded file content or raw content
        mime_type: MIME type of the file (auto-detected if not provided)
    
    Returns:
        dict: File metadata including webViewLink, or {'error': ...} on error
    """
    print(f"DEBUG: upload_to_drive called with file_name={file_name}, mime_type={mime_type}")
    print(f"DEBUG: file_content length={len(file_content) if file_content else 0}")
    
    service = get_drive_service()
    
    if not service:
        print("DEBUG: Not authenticated with Google Drive")
        return {'error': 'Not authenticated with Google Drive'}
    
    try:
        import base64
        
        # Handle base64 content
        if isinstance(file_content, str) and len(file_content) > 1000:
            # Likely base64
            try:
                file_data = base64.b64decode(file_content)
                print(f"DEBUG: Decoded base64, file_data length={len(file_data)}")
            except Exception as e:
                print(f"DEBUG: base64 decode failed: {e}")
                file_data = file_content.encode('utf-8')
        else:
            file_data = file_content.encode('utf-8') if isinstance(file_content, str) else file_content
            print(f"DEBUG: Using raw content, length={len(file_data)}")
        
        # Detect mime type if not provided
        if mime_type is None:
            import mimetypes
            mime_type, _ = mimetypes.guess_type(file_name)
            if mime_type is None:
                mime_type = 'application/octet-stream'
        
        print(f"DEBUG: Final mime_type={mime_type}")
        
        file_metadata = {
            'name': file_name,
            'mimeType': mime_type
        }
        
        media = MediaInMemoryUpload(
            file_data,
            mimetype=mime_type,
            resumable=True
        )
        
        print("DEBUG: Creating file in Drive...")
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id,name,webViewLink,webContentLink'
        ).execute()
        
        print(f"DEBUG: File created with id={file.get('id')}")
        
        # Make file accessible via link
        try:
            service.permissions().create(
                fileId=file['id'],
                body={'type': 'anyone', 'role': 'reader'},
                sendNotificationEmail=False
            ).execute()
            print(f"DEBUG: File permissions set to public")
        except Exception as perm_error:
            print(f"DEBUG: Could not set public permissions (file may already be public or different ownership): {perm_error}")
        
        return {
            'id': file['id'],
            'name': file['name'],
            'webViewLink': file.get('webViewLink'),
            'webContentLink': file.get('webContentLink'),
            'fileUrl': file.get('webContentLink') or file.get('webViewLink')  # Prefer direct download link for attachments
        }
    except Exception as e:
        print(f"DEBUG: upload_to_drive exception: {e}")
        return {'error': str(e)}


def download_and_reupload_drive_file(file_id, new_name=None):
    """
    Download a file from Google Drive and re-upload it to get ownership.
    
    Args:
        file_id: The ID of the file to download
        new_name: Optional new name for the file (defaults to original)
    
    Returns:
        dict: File metadata of the uploaded file, or {'error': ...} on error
    """
    service = get_drive_service()
    
    if not service:
        return {'error': 'Not authenticated with Google Drive'}
    
    try:
        # Get file metadata
        file_metadata = service.files().get(fileId=file_id, fields='id,name,mimeType').execute()
        
        # Download file content
        request = service.files().get_media(fileId=file_id)
        file_content = request.execute()
        
        # Re-upload with new ownership
        upload_name = new_name or file_metadata.get('name', 'Untitled')
        upload_mime_type = file_metadata.get('mimeType', 'application/octet-stream')
        
        result = upload_to_drive(upload_name, file_content, upload_mime_type)
        
        if 'error' not in result:
            print(f"DEBUG: Re-uploaded file as: {result.get('name')} (ID: {result.get('id')})")
        
        return result
    except Exception as e:
        print(f"Error downloading/reuploading Drive file: {e}")
        return {'error': str(e)}

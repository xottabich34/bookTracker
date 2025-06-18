"""
Тесты для проверки авторизации пользователей
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from main import owner_only


class TestAuthorization:
    """Тесты авторизации пользователей"""
    
    @pytest.mark.asyncio
    async def test_owner_only_allowed_user(self, mock_update, mock_context, allowed_user_id):
        """Тест: разрешенный пользователь может выполнять команды"""
        # Arrange
        mock_update.effective_user.id = allowed_user_id
        mock_function = AsyncMock(return_value="success")
        decorated_function = owner_only(mock_function)
        
        # Act
        result = await decorated_function(mock_update, mock_context)
        
        # Assert
        assert result == "success"
        mock_function.assert_called_once_with(mock_update, mock_context)
    
    @pytest.mark.asyncio
    async def test_owner_only_blocked_user(self, mock_update, mock_context, blocked_user_id):
        """Тест: заблокированный пользователь получает отказ"""
        # Arrange
        mock_update.effective_user.id = blocked_user_id
        mock_function = AsyncMock(return_value="success")
        decorated_function = owner_only(mock_function)
        
        # Act
        result = await decorated_function(mock_update, mock_context)
        
        # Assert
        assert result is None
        mock_function.assert_not_called()
        mock_update.message.reply_text.assert_called_once()
        assert "доступ запрещён" in mock_update.message.reply_text.call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_owner_only_no_effective_user(self, mock_context):
        """Тест: обработка случая без effective_user"""
        # Arrange
        mock_update = MagicMock()
        mock_update.effective_user = None
        mock_update.message = MagicMock()
        mock_update.message.reply_text = AsyncMock()
        
        mock_function = AsyncMock(return_value="success")
        decorated_function = owner_only(mock_function)
        
        # Act
        result = await decorated_function(mock_update, mock_context)
        
        # Assert
        assert result is None
        mock_function.assert_not_called()
        mock_update.message.reply_text.assert_called_once_with("Ошибка: пользователь не найден.")
    
    @pytest.mark.asyncio
    async def test_owner_only_no_message(self, mock_context):
        """Тест: обработка случая без message"""
        # Arrange
        mock_update = MagicMock()
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = 12345
        mock_update.message = None
        
        mock_function = AsyncMock(return_value="success")
        decorated_function = owner_only(mock_function)
        
        # Act
        result = await decorated_function(mock_update, mock_context)
        
        # Assert
        assert result is None
        mock_function.assert_not_called() 
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title ProductRegistry
 * @dev Smart Contract for immutable product registration and verification on Ethereum testnets (Ganache).
 * Specifically designed for Footwear Anti-Counterfeit Verification with cryptographic SHA-256 validation.
 */
contract ProductRegistry {
    // Contract Owner / System Admin
    address public owner;

    // Structure representing an authenticated product registered by a certified manufacturer
    struct Product {
        string productId;        // Unique business identifier (e.g., "NIKE-AF1-8921")
        string brand;            // Brand Name (e.g., "Nike", "Adidas")
        string batchNo;          // Manufacturing Batch Number
        uint256 mfgTimestamp;    // Manufacturing Unix Timestamp
        bytes32 dataHash;        // SHA-256 cryptographic hash of metadata
        address manufacturer;    // Ethereum address of the manufacturer who registered the product
        bool isRegistered;       // Registration existence flag
    }

    // Mapping from unique productId to the immutable Product record
    mapping(string => Product) private products;

    // Authorized manufacturers list (address => status)
    mapping(address => bool) public authorizedManufacturers;

    // Keep count of total registered products
    uint256 public totalProductsRegistered;

    // Events for distributed ledger audit logging
    event ManufacturerAuthorized(address indexed manufacturer);
    event ManufacturerRevoked(address indexed manufacturer);
    event ProductRegistered(
        string indexed productId,
        string brand,
        string batchNo,
        bytes32 dataHash,
        address indexed manufacturer,
        uint256 timestamp
    );

    // Modifiers
    modifier onlyOwner() {
        require(msg.sender == owner, "ProductRegistry: Caller is not the contract owner");
        _;
    }

    modifier onlyAuthorizedManufacturer() {
        require(
            authorizedManufacturers[msg.sender] || msg.sender == owner,
            "ProductRegistry: Caller is not an authorized manufacturer"
        );
        _;
    }

    /**
     * @dev Constructor initializes the deployer as owner and default authorized manufacturer.
     */
    constructor() {
        owner = msg.sender;
        authorizedManufacturers[msg.sender] = true;
        emit ManufacturerAuthorized(msg.sender);
    }

    /**
     * @dev Authorize a manufacturer wallet address.
     * @param _manufacturer Address to grant registration permissions.
     */
    function authorizeManufacturer(address _manufacturer) external onlyOwner {
        require(_manufacturer != address(0), "ProductRegistry: Invalid address");
        authorizedManufacturers[_manufacturer] = true;
        emit ManufacturerAuthorized(_manufacturer);
    }

    /**
     * @dev Revoke an authorized manufacturer.
     * @param _manufacturer Address to revoke permissions from.
     */
    function revokeManufacturer(address _manufacturer) external onlyOwner {
        require(_manufacturer != owner, "ProductRegistry: Cannot revoke contract owner");
        authorizedManufacturers[_manufacturer] = false;
        emit ManufacturerRevoked(_manufacturer);
    }

    /**
     * @dev Registers a new product and seals its cryptographic hash permanently on the blockchain.
     * @param _productId Unique alphanumeric ID for the product
     * @param _brand Footwear brand name
     * @param _batchNo Batch identification code
     * @param _mfgTimestamp Timestamp of product creation
     * @param _dataHash 32-byte cryptographic SHA-256 hash of product attributes
     */
    function registerProduct(
        string memory _productId,
        string memory _brand,
        string memory _batchNo,
        uint256 _mfgTimestamp,
        bytes32 _dataHash
    ) external onlyAuthorizedManufacturer {
        require(bytes(_productId).length > 0, "ProductRegistry: Product ID cannot be empty");
        require(!products[_productId].isRegistered, "ProductRegistry: Product is already registered on-chain");
        require(_dataHash != bytes32(0), "ProductRegistry: Invalid data hash");

        products[_productId] = Product({
            productId: _productId,
            brand: _brand,
            batchNo: _batchNo,
            mfgTimestamp: _mfgTimestamp,
            dataHash: _dataHash,
            manufacturer: msg.sender,
            isRegistered: true
        });

        totalProductsRegistered += 1;

        emit ProductRegistered(
            _productId,
            _brand,
            _batchNo,
            _dataHash,
            msg.sender,
            _mfgTimestamp
        );
    }

    /**
     * @dev View function to retrieve and verify immutable product specifications.
     * @param _productId Product ID to query
     * @return isRegistered True if found on-chain
     * @return brand Brand name
     * @return batchNo Manufacturing batch
     * @return mfgTimestamp Manufacturing timestamp
     * @return dataHash Cryptographic SHA-256 hash stored on-chain
     * @return manufacturer Ethereum address of registering manufacturer
     */
    function verifyProduct(string memory _productId)
        external
        view
        returns (
            bool isRegistered,
            string memory brand,
            string memory batchNo,
            uint256 mfgTimestamp,
            bytes32 dataHash,
            address manufacturer
        )
    {
        Product memory p = products[_productId];
        return (
            p.isRegistered,
            p.brand,
            p.batchNo,
            p.mfgTimestamp,
            p.dataHash,
            p.manufacturer
        );
    }

    /**
     * @dev Quick check if a product exists on-chain.
     */
    function isProductRegistered(string memory _productId) external view returns (bool) {
        return products[_productId].isRegistered;
    }
}

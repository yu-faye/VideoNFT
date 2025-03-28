// mintVideoNFTWithCircomZKP.js

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const IPFS = require('ipfs-http-client');
const Web3 = require('web3').default || require('web3');

// 读取 VideoNFT 合约构件
const videoNFTArtifactPath = path.join(process.cwd(), 'build/contracts/VideoNFT.json');
const videoNFTArtifact = JSON.parse(fs.readFileSync(videoNFTArtifactPath, 'utf8'));

// 读取 Verifier 合约构件（生成的 Verifier.sol 后经 Truffle 编译生成的文件）
const verifierArtifactPath = path.join(process.cwd(), 'build/contracts/Verifier.json');
const verifierArtifact = JSON.parse(fs.readFileSync(verifierArtifactPath, 'utf8'));

// 配置 IPFS 客户端（假设使用本地 IPFS 节点）
const ipfs = IPFS.create({ host: 'localhost', port: 5001, protocol: 'http' });

// 配置 Web3 连接到 Ganache
const web3 = new Web3("http://127.0.0.1:8545");

// 获取 VideoNFT 合约部署信息
const videoNFTNetworks = Object.keys(videoNFTArtifact.networks);
if (videoNFTNetworks.length === 0) {
    throw new Error("未找到 VideoNFT 合约部署信息，请先部署合约");
}
const videoNFTNetworkId = videoNFTNetworks[0];
const videoNFTDeployed = videoNFTArtifact.networks[videoNFTNetworkId];
const videoNFTAddress = videoNFTDeployed.address;
const videoNFTABI = videoNFTArtifact.abi;
const videoNFTInstance = new web3.eth.Contract(videoNFTABI, videoNFTAddress);

// 获取 Verifier 合约部署信息
const verifierNetworks = Object.keys(verifierArtifact.networks);
if (verifierNetworks.length === 0) {
    throw new Error("未找到 Verifier 合约部署信息，请先部署合约");
}
const verifierNetworkId = verifierNetworks[0];
const verifierDeployed = verifierArtifact.networks[verifierNetworkId];
const verifierAddress = verifierDeployed.address;
const verifierABI = verifierArtifact.abi;
const verifierInstance = new web3.eth.Contract(verifierABI, verifierAddress);

// 计算视频文件的 SHA256 哈希（作为视频指纹）
function computeFileHash(filePath) {
    const fileBuffer = fs.readFileSync(filePath);
    const hash = crypto.createHash('sha256');
    hash.update(fileBuffer);
    return hash.digest('hex');
}

// 主流程：上传视频 -> 计算视频哈希 -> 读取 proof 与公共信号 -> 调用 Verifier 合约验证证明 -> 铸造 NFT
async function mintNFTWithZKP(filePath) {
    try {
        // 上传视频到 IPFS
        const fileData = fs.readFileSync(filePath);
        console.log("上传视频到 IPFS...");
        const ipfsResult = await ipfs.add(fileData);
        console.log("视频上传成功，CID:", ipfsResult.path);

        // 计算视频文件的 SHA256 哈希
        const videoHash = computeFileHash(filePath);
        console.log("视频 SHA256 哈希:", videoHash);
        // 转换为大整数字符串（供电路使用），例如：
        const videoHashNumeric = BigInt('0x' + videoHash).toString();

        // 读取证明文件 proof.json 和公共信号 public.json（确保已由 circom+snarkjs 生成）
        const proofPath = path.join(process.cwd(), 'proof.json');
        const publicPath = path.join(process.cwd(), 'public.json');
        if (!fs.existsSync(proofPath) || !fs.existsSync(publicPath)) {
            throw new Error("未找到 proof.json 或 public.json 文件，请先生成证明");
        }
        const proofData = JSON.parse(fs.readFileSync(proofPath, 'utf8'));
        const publicData = JSON.parse(fs.readFileSync(publicPath, 'utf8'));
        // publicData 通常是个数组，例如：["videoHashNumeric"]

        // 调用 Verifier 合约验证证明
        console.log("验证零知识证明...");
        const verified = await verifierInstance.methods.verifyingKey(
            proofData.pi_a,
            proofData.pi_b,
            proofData.pi_c,
            publicData
        ).call();
        console.log("证明验证结果:", verified);
        if (!verified) {
            throw new Error("零知识证明验证失败");
        }

        // 如果验证通过，调用 NFT 合约铸造 NFT
        const tokenURI = `ipfs://${ipfsResult.path}`;
        const accounts = await web3.eth.getAccounts();
        const defaultAccount = accounts[0];
        console.log("证明验证成功，铸造 NFT，tokenURI:", tokenURI);
        const mintReceipt = await videoNFTInstance.methods.mintVideoNFT(defaultAccount, tokenURI)
            .send({ from: defaultAccount, gas: 300000, gasPrice: web3.utils.toWei('20', 'gwei') });
        console.log("NFT 铸造成功，交易收据:", mintReceipt);
    } catch (err) {
        console.error("NFT 铸造过程出错:", err);
    }
}

// 假设 video.mp4 位于项目根目录
const videoFilePath = path.join(process.cwd(), 'video.mp4');
mintNFTWithZKP(videoFilePath);
